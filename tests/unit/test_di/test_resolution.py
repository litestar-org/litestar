from __future__ import annotations

import asyncio
from typing import Any

import pytest

from litestar.di import DIContext, NamedDependency, provide
from tests.unit.test_di.helpers import Resolve, registry_with_providers, slot_of


async def test_concurrent_awaits_invoke_factory_once() -> None:
    calls = 0

    @provide(scope="app")
    async def value() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return 42

    async with DIContext(registry_with_providers(value)) as ctx:
        results = await asyncio.gather(*(ctx.solve("value") for _ in range(50)))

    assert results == [42] * 50
    assert calls == 1


async def test_value_cached_across_sequential_awaits(resolve: Resolve) -> None:
    calls = 0

    @provide(scope="app")
    async def value() -> object:
        nonlocal calls
        calls += 1
        return object()

    async with DIContext(registry_with_providers(value)) as ctx:
        first = await resolve(ctx, "value")
        second = await resolve(ctx, "value")

    assert first is second
    assert calls == 1


async def test_cancelling_producer_hands_production_to_next_caller() -> None:
    """
    A production runs in the caller that started it, so cancelling that caller cancels
    the production. if there's another waiter, the next caller should take over
    """
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    @provide(scope="app")
    async def slow() -> int:
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return 7

    async with DIContext(registry_with_providers(slow)) as ctx:
        first = asyncio.create_task(ctx.solve("slow"))
        second = asyncio.create_task(ctx.solve("slow"))
        await started.wait()
        await asyncio.sleep(0)  # let 'second' land on the slot as a waiter

        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first

        # 'second' was next in line for the lock, should be producing now
        await started.wait()
        release.set()
        assert await second == 7
        assert ctx.get("slow") == 7

    assert calls == 2  # once per resolution, not once ever. the cancelled attempt is redone


async def test_interrupted_production_leaves_slot_empty() -> None:
    """no other waiters, so the slot should be empty again, and the provider not locked"""
    started = asyncio.Event()
    release = asyncio.Event()
    calls = 0

    @provide(scope="app")
    async def slow() -> int:
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return 7

    async with DIContext(registry_with_providers(slow)) as ctx:
        first = asyncio.create_task(ctx.solve("slow"))
        await started.wait()
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first

        slot = slot_of(ctx, slow)
        assert slot.running is False
        assert slot.done is False
        assert slot._lock is not None and not slot._lock.locked()

        release.set()
        assert await ctx.solve("slow") == 7

    assert calls == 2


async def test_failing_factory_retried_by_every_caller() -> None:
    calls = 0

    @provide(scope="app")
    async def boom() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        if calls < 7:
            raise RuntimeError(f"attempt {calls} failed")
        return calls

    async with DIContext(registry_with_providers(boom)) as ctx:
        results = await asyncio.gather(*(ctx.solve("boom") for _ in range(5)), return_exceptions=True)
        assert all(isinstance(result, RuntimeError) for result in results)
        assert len({id(result) for result in results}) == 5  # one attempt each, queued on the lock
        assert slot_of(ctx, boom).done is False

        with pytest.raises(RuntimeError, match="attempt 6 failed"):
            await ctx.solve("boom")
        assert await ctx.solve("boom") == 7  # the factory recovered, and so did the key

    assert calls == 7


async def test_factory_exception_annotated_with_dependency() -> None:
    @provide(scope="app")
    async def boom() -> int:
        raise RuntimeError("factory failed")

    async with DIContext(registry_with_providers(boom)) as ctx:
        with pytest.raises(RuntimeError) as exc_info:
            await ctx.solve("boom")

    assert any("Raised while resolving dependency 'boom'" in note for note in exc_info.value.__notes__)
    assert any("scope='app'" in note for note in exc_info.value.__notes__)


async def test_failing_sub_dependency_raises_unwrapped() -> None:
    @provide(scope="app")
    async def inner() -> int:
        raise ValueError("inner failed")

    @provide(scope="app")
    async def outer(inner: NamedDependency[int]) -> int:
        return inner

    async with DIContext(registry_with_providers(inner, outer)) as ctx:
        with pytest.raises(ValueError, match="inner failed"):
            await ctx.solve("outer")


async def test_production_runs_in_caller_task_and_context() -> None:
    # should run in-line, not e.g. a separate context or task
    running_in: list[asyncio.Task[Any] | None] = []

    @provide(scope="app")
    async def value() -> int:
        running_in.append(asyncio.current_task())
        return 1

    async with DIContext(registry_with_providers(value)) as ctx:
        caller = asyncio.create_task(ctx.solve("value"))
        await caller

    assert running_in == [caller]


async def test_cancelled_waiter_does_not_affect_production_or_other_waiters() -> None:
    gate = asyncio.Event()
    calls = 0

    @provide(scope="app")
    async def slow() -> int:
        nonlocal calls
        calls += 1
        await gate.wait()
        return 7

    async with DIContext(registry_with_providers(slow)) as ctx:
        producer = asyncio.create_task(ctx.solve("slow"))
        await asyncio.sleep(0)  # the producer claims the slot
        leaving = asyncio.create_task(ctx.solve("slow"))
        staying = asyncio.create_task(ctx.solve("slow"))
        await asyncio.sleep(0)  # both waiters wait for the slot's lock

        leaving.cancel()
        with pytest.raises(asyncio.CancelledError):
            await leaving

        gate.set()
        assert await producer == 7
        assert await staying == 7
        assert ctx.get("slow") == 7

    assert calls == 1


async def test_failing_dependency_raises_again_on_retry() -> None:
    @provide(scope="app")
    async def inner() -> int:
        raise ValueError("inner failed")

    @provide(scope="app")
    async def outer(inner: NamedDependency[int]) -> int:
        return inner

    async with DIContext(registry_with_providers(inner, outer)) as ctx:
        # the second attempt must fail the same way rather than wait on an unfilled slot
        with pytest.raises(ValueError, match="inner failed"):
            await ctx.solve("outer")

        with pytest.raises(ValueError, match="inner failed"):
            await ctx.solve("outer")


async def test_diamond_dependency_resolves_shared_node_once() -> None:
    calls = 0

    @provide(scope="app")
    async def base() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return 1

    @provide(scope="app")
    async def left(base: NamedDependency[int]) -> int:
        return base + 1

    @provide(scope="app")
    async def right(base: NamedDependency[int]) -> int:
        return base + 2

    @provide(scope="app")
    async def top(left: NamedDependency[int], right: NamedDependency[int]) -> int:
        return left + right

    async with DIContext(registry_with_providers(base, left, right, top)) as ctx:
        assert await ctx.solve("top") == 5

    assert calls == 1


async def test_provider_raising_cancellation_re_raises_without_caching() -> None:
    # the slot should be reset, so every later caller runs the factory again
    attempts = 0

    @provide(scope="app")
    async def flaky() -> int:
        nonlocal attempts
        attempts += 1
        raise asyncio.CancelledError

    async with DIContext(registry_with_providers(flaky)) as ctx:
        for _ in range(2):
            caller = asyncio.create_task(ctx.solve("flaky"))
            with pytest.raises(asyncio.CancelledError):
                await caller
            assert caller.cancelled() is True

    assert attempts == 2


@pytest.mark.parametrize("exception", [SystemExit, KeyboardInterrupt])
async def test_system_exit_and_keyboard_interrupt_raise(exception: type[Exception]) -> None:
    @provide(scope="app")
    async def quits() -> int:
        raise exception()

    async with DIContext(registry_with_providers(quits)) as ctx:
        with pytest.raises(exception):
            await ctx.solve("quits")


async def test_cancelled_error_during_production_is_not_set_as_result() -> None:
    # A future somebody else cancels throws 'CancelledError' into the provider. it
    # should not be bubbled up from there, to not potentially cancel callers that were
    # never explicitly cancelled
    attempts = 0

    @provide(scope="app")
    async def engine() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            inner = asyncio.ensure_future(asyncio.sleep(10))
            asyncio.get_running_loop().call_soon(inner.cancel)
            await asyncio.shield(inner)
        return "engine"

    async with DIContext(registry_with_providers(engine)) as ctx:
        with pytest.raises(asyncio.CancelledError):
            await ctx.solve("engine")
        slot = slot_of(ctx, engine)
        assert slot.done is False and slot.running is False

        assert await ctx.solve("engine") == "engine"

    assert attempts == 2


async def test_cancelled_error_during_production_doesnt_settle_dependent() -> None:
    attempts = {"engine": 0, "service": 0}

    @provide(scope="app")
    async def engine() -> str:
        attempts["engine"] += 1
        if attempts["engine"] == 1:
            inner = asyncio.ensure_future(asyncio.sleep(10))
            asyncio.get_running_loop().call_soon(inner.cancel)
            await asyncio.shield(inner)
        return "engine"

    @provide(scope="app")
    async def service(engine: NamedDependency[str]) -> str:
        attempts["service"] += 1
        return f"service({engine})"

    async with DIContext(registry_with_providers(engine, service)) as ctx:
        with pytest.raises(asyncio.CancelledError):
            await ctx.solve("service")
        for provider in (engine, service):
            slot = slot_of(ctx, provider)
            assert slot.done is False and slot.running is False

        assert await ctx.solve("service") == "service(engine)"

    assert attempts == {"engine": 2, "service": 1}


async def test_waiter_picks_up_cancelled_production() -> None:
    # with 2 concurrent waiters for a solve, if one of them is cancelled, the second
    # one should be able to pick up production
    started = asyncio.Event()
    attempts = 0

    @provide(scope="app")
    async def engine() -> str:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            started.set()
            inner = asyncio.ensure_future(asyncio.Event().wait())
            await asyncio.sleep(0)  # let the waiter arrive
            inner.cancel()
            await asyncio.shield(inner)
        return "engine"

    async with DIContext(registry_with_providers(engine)) as ctx:
        producer = asyncio.create_task(ctx.solve("engine"))
        await started.wait()
        waiter = asyncio.create_task(ctx.solve("engine"))

        with pytest.raises(asyncio.CancelledError):
            await producer
        assert await waiter == "engine"

    assert attempts == 2
