# pyright: reportUnnecessaryTypeIgnoreComment=false
from __future__ import annotations

import asyncio
import threading
from collections.abc import AsyncGenerator, Generator
from typing import Any

import anyio
import pytest

from litestar.di import (
    DIContext,
    DIRegistry,
    NamedDependency,
    provide,
)
from litestar.di.context import _IS_PY_313_PLUS, _CleanupStack
from litestar.di.exceptions import DIContextClosedError, DIScopeError
from tests.unit.test_di.helpers import Resolve, slot_of


async def test_cleanup_runs_on_context_close(resolve: Resolve) -> None:
    events: list[str] = []

    @provide(scope="app")
    async def resource() -> AsyncGenerator[str, None]:
        events.append("up")
        yield "value"
        events.append("down")

    async with DIContext(DIRegistry("app", [resource])) as ctx:
        assert await resolve(ctx, "resource") == "value"
        assert events == ["up"]

    assert events == ["up", "down"]


async def test_unused_provider_never_opened() -> None:
    events: list[str] = []

    @provide(scope="app")
    async def resource() -> AsyncGenerator[str, None]:
        events.append("up")
        yield "value"
        events.append("down")

    async with DIContext(DIRegistry("app", [resource])):
        pass

    assert events == []


async def test_dependencies_torn_down_after_dependents() -> None:
    events: list[str] = []

    @provide(scope="app")
    async def base() -> AsyncGenerator[str, None]:
        events.append("base up")
        yield "base"
        events.append("base down")

    @provide(scope="app")
    async def derived(base: NamedDependency[str]) -> AsyncGenerator[str, None]:
        events.append("derived up")
        yield f"derived({base})"
        events.append("derived down")

    async with DIContext(DIRegistry("app", [base, derived])) as ctx:
        await ctx.solve("derived")

    assert events == ["base up", "derived up", "derived down", "base down"]


async def test_shared_dependency_torn_down_after_all_dependents() -> None:
    events: list[str] = []

    @provide(scope="app", key="base")
    async def provide_base() -> AsyncGenerator[str, None]:
        events.append("base up")
        await asyncio.sleep(0)
        yield "base"
        events.append("base down")

    @provide(scope="app", key="left")
    async def provide_left(base: NamedDependency[str]) -> AsyncGenerator[str, None]:
        events.append("left up")
        yield "left"
        events.append("left down")

    @provide(scope="app", key="right")
    async def provide_right(base: NamedDependency[str]) -> AsyncGenerator[str, None]:
        events.append("right up")
        yield "right"
        events.append("right down")

    async with DIContext(DIRegistry("app", [provide_base, provide_left, provide_right])) as ctx:
        await ctx.solve_many("left", "right")

    assert events[0] == "base up"
    assert events[-1] == "base down"
    # both dependents come down before the value they were built from
    assert events.index("left down") < events.index("base down")
    assert events.index("right down") < events.index("base down")


async def test_nested_contexts_tear_down_inner_first() -> None:
    events: list[str] = []

    @provide(scope="app")
    async def app_resource() -> AsyncGenerator[str, None]:
        yield "app"
        events.append("app down")

    @provide(scope="request")
    async def request_resource() -> AsyncGenerator[str, None]:
        yield "request"
        events.append("request down")

    registry = DIRegistry("app", [app_resource, request_resource])
    async with DIContext(registry) as app_ctx:
        await app_ctx.solve("app_resource")
        async with app_ctx.enter_nested() as req:
            await req.solve("request_resource")
        assert events == ["request down"]

    assert events == ["request down", "app down"]


async def test_request_scoped_resource_recreated_per_request(resolve: Resolve) -> None:
    events: list[str] = []

    @provide(scope="request")
    async def resource() -> AsyncGenerator[int, None]:
        events.append("up")
        yield len(events)
        events.append("down")

    registry = DIRegistry("app", [resource])
    async with DIContext(registry) as app_ctx:
        async with app_ctx.enter_nested() as req:
            await resolve(req, "resource")
        async with app_ctx.enter_nested() as req:
            await resolve(req, "resource")

    assert events == ["up", "down", "up", "down"]


async def test_cleanup_receives_body_exception() -> None:
    seen: list[BaseException | None] = []

    @provide(scope="app")
    async def resource() -> AsyncGenerator[str, None]:
        try:
            yield "value"
        except BaseException as exc:
            seen.append(exc)
            raise
        else:
            seen.append(None)

    with pytest.raises(ValueError, match="from the body"):
        async with DIContext(DIRegistry("app", [resource])) as ctx:
            await ctx.solve("resource")
            raise ValueError("from the body")

    assert len(seen) == 1
    assert isinstance(seen[0], ValueError)


async def test_code_after_bare_yield_skipped_when_body_raises() -> None:
    events: list[str] = []

    @provide(scope="app")
    async def bare() -> AsyncGenerator[str, None]:
        yield "bare"
        events.append("bare down")

    @provide(scope="app")
    async def guarded() -> AsyncGenerator[str, None]:
        try:
            yield "guarded"
        finally:
            events.append("guarded down")

    with pytest.raises(ValueError, match="from the body"):
        async with DIContext(DIRegistry("app", [bare, guarded])) as ctx:
            await ctx.solve_many("bare", "guarded")
            raise ValueError("from the body")

    assert events == ["guarded down"]


async def test_cleanup_cannot_suppress_body_exception() -> None:

    @provide(scope="app")
    async def swallowing() -> AsyncGenerator[str, None]:
        try:
            yield "value"
        except ValueError:
            pass  # deliberately tries to suppress

    with pytest.raises(ValueError, match="from the body"):
        async with DIContext(DIRegistry("app", [swallowing])) as ctx:
            await ctx.solve("swallowing")
            raise ValueError("from the body")


async def test_single_cleanup_failure_raises_unwrapped() -> None:
    @provide(scope="app")
    async def resource() -> AsyncGenerator[str, None]:
        yield "value"
        raise RuntimeError("cleanup failed")

    with pytest.raises(RuntimeError, match="cleanup failed") as exc_info:
        async with DIContext(DIRegistry("app", [resource])) as ctx:
            await ctx.solve("resource")

    assert any("tearing down dependency 'resource'" in note for note in exc_info.value.__notes__)


async def test_multiple_cleanup_failures_raise_exception_group() -> None:
    @provide(scope="app")
    async def first() -> AsyncGenerator[str, None]:
        yield "first"
        raise RuntimeError("first failed")

    @provide(scope="app")
    async def second() -> AsyncGenerator[str, None]:
        yield "second"
        raise RuntimeError("second failed")

    with pytest.raises(ExceptionGroup) as exc_info:
        async with DIContext(DIRegistry("app", [first, second])) as ctx:
            await ctx.solve_many("first", "second")

    messages = {str(exc) for exc in exc_info.value.exceptions}
    assert messages == {"first failed", "second failed"}


async def test_failing_cleanup_does_not_stop_others() -> None:
    events: list[str] = []

    @provide(scope="app")
    async def failing() -> AsyncGenerator[str, None]:
        yield "failing"
        raise RuntimeError("boom")

    @provide(scope="app")
    async def other() -> AsyncGenerator[str, None]:
        yield "other"
        # Code after a bare yield runs only when the generator is resumed normally, so
        # this line running shows the cleanup was not handed 'failing''s error, only
        # that it still ran
        events.append("other down")

    with pytest.raises(RuntimeError, match="boom"):
        async with DIContext(DIRegistry("app", [failing, other])) as ctx:
            await ctx.solve_many("other", "failing")

    assert events == ["other down"]


async def test_generator_yielding_twice_raises() -> None:
    @provide(scope="app")
    async def twice() -> AsyncGenerator[int, None]:
        yield 1
        yield 2

    with pytest.raises(RuntimeError, match="didn't stop") as exc_info:
        async with DIContext(DIRegistry("app", [twice])) as ctx:
            await ctx.solve("twice")

    assert any("tearing down dependency 'twice'" in note for note in exc_info.value.__notes__)


async def test_generator_that_never_yields_raises() -> None:
    @provide(scope="app")
    async def never() -> AsyncGenerator[int, None]:
        return
        yield 1  # type: ignore[unreachable]

    async with DIContext(DIRegistry("app", [never])) as ctx:
        with pytest.raises(RuntimeError, match="didn't yield") as exc_info:
            await ctx.solve("never")

    assert any("resolving dependency 'never'" in note for note in exc_info.value.__notes__)


async def test_sync_generator_yielding_twice_raises() -> None:
    @provide(scope="app")
    def twice() -> Generator[int, None, None]:
        yield 1
        yield 2

    with pytest.raises(RuntimeError, match="didn't stop") as exc_info:
        async with DIContext(DIRegistry("app", [twice])) as ctx:
            await ctx.solve("twice")

    assert any("tearing down dependency 'twice'" in note for note in exc_info.value.__notes__)


async def test_sync_generator_that_never_yields_raises() -> None:
    @provide(scope="app")
    def never() -> Generator[int, None, None]:
        return
        yield 1  # type: ignore[unreachable]

    async with DIContext(DIRegistry("app", [never])) as ctx:
        with pytest.raises(RuntimeError, match="didn't yield") as exc_info:
            await ctx.solve("never")

    assert any("resolving dependency 'never'" in note for note in exc_info.value.__notes__)


async def test_provider_failing_during_setup_registers_no_cleanup() -> None:
    events: list[str] = []

    @provide(scope="app")
    async def good() -> AsyncGenerator[str, None]:
        yield "good"
        events.append("good down")

    @provide(scope="app")
    async def bad() -> AsyncGenerator[str, None]:
        raise RuntimeError("setup failed")
        yield "bad"  # type: ignore[unreachable]

    async with DIContext(DIRegistry("app", [good, bad])) as ctx:
        await ctx.solve("good")
        with pytest.raises(RuntimeError, match="setup failed"):
            await ctx.solve("bad")

    assert events == ["good down"]


async def test_closing_twice_is_fine() -> None:
    events: list[str] = []

    @provide(scope="app")
    async def resource() -> AsyncGenerator[str, None]:
        yield "value"
        events.append("down")

    ctx = DIContext(DIRegistry("app", [resource]))
    await ctx.__aenter__()
    await ctx.solve("resource")
    await ctx.__aexit__(None, None, None)
    await ctx.__aexit__(None, None, None)

    assert events == ["down"]


async def test_closing_child_after_parent_raises_at_both_ends() -> None:
    # closing the parent raises naming, and closing the child afterwards raises as well,
    # and still tears down the child's values. in between, the child cannot be used
    events: list[str] = []

    @provide(scope="request")
    async def resource() -> AsyncGenerator[str, None]:
        yield "value"
        events.append("down")

    registry = DIRegistry("app", [resource])
    app_ctx = DIContext(registry)
    await app_ctx.__aenter__()
    req = DIContext(registry, parent=app_ctx)
    await req.__aenter__()
    await req.solve("resource")

    with pytest.raises(
        DIScopeError, match=r"was closed while 1 nested context\(s\) under it had not yet been closed"
    ) as at_the_parent:
        await app_ctx.__aexit__(None, None, None)
    assert repr(req) in str(at_the_parent.value)
    assert events == []  # the child's values are the child's to tear down

    with pytest.raises(DIContextClosedError, match=".*cannot be used, because a parent context of it is closed"):
        await req.solve("resource")  # its own, already resolved value: raises all the same
    with pytest.raises(DIContextClosedError, match=".*cannot be used, because a parent context of it is closed"):
        req.get("resource")

    with pytest.raises(DIScopeError, match="was closed after its parent"):
        await req.__aexit__(None, None, None)
    assert events == ["down"]


async def test_out_of_order_close_is_reported_even_when_cleanup_fails() -> None:

    @provide(scope="request")
    async def resource() -> AsyncGenerator[str, None]:
        yield "value"
        raise RuntimeError("cleanup failed")

    registry = DIRegistry("app", [resource])
    app_ctx = DIContext(registry)
    await app_ctx.__aenter__()
    req = DIContext(registry, parent=app_ctx)
    await req.__aenter__()
    await req.solve("resource")

    with pytest.raises(DIScopeError, match=r"was closed while 1 nested context\(s\) under it had not yet been closed"):
        await app_ctx.__aexit__(None, None, None)
    with pytest.raises(DIScopeError, match="was closed after its parent") as exc_info:
        await req.__aexit__(None, None, None)

    assert isinstance(exc_info.value.__context__, RuntimeError)
    assert str(exc_info.value.__context__) == "cleanup failed"
    assert req.closed


async def test_parent_closing_during_childs_teardown_raises() -> None:  # codespell:ignore
    # order shouldn't matter, it should always raise
    cleanup_started = asyncio.Event()
    release = asyncio.Event()

    @provide(scope="request")
    async def resource() -> AsyncGenerator[str, None]:
        yield "value"
        cleanup_started.set()
        await release.wait()

    registry = DIRegistry("app", [resource])
    app_ctx = DIContext(registry)
    await app_ctx.__aenter__()
    req = DIContext(registry, parent=app_ctx)
    await req.__aenter__()
    await req.solve("resource")

    closing = asyncio.create_task(req.__aexit__(None, None, None))
    await cleanup_started.wait()
    with pytest.raises(DIScopeError, match=r"was closed while 1 nested context\(s\) under it had not yet been closed"):
        await app_ctx.__aexit__(None, None, None)  # the child is closing, not closed: raises at the end
    release.set()
    with pytest.raises(DIScopeError, match="was closed after its parent"):
        await closing


async def test_parent_reports_child_left_open_in_a_task_its_block_did_not_wait_for() -> None:
    """The report lands in the task that owns the parent's block: a task started inside it entered a
    nested context and was still running when the block ended."""
    release = asyncio.Event()

    @provide(scope="request")
    async def request_value() -> object:
        return object()

    async def request_task(app_ctx: DIContext) -> None:
        async with app_ctx.enter_nested() as req:
            await req.solve("request_value")
            await release.wait()

    task: asyncio.Task[None] | None = None
    with pytest.raises(
        DIScopeError, match=r"was closed while 1 nested context\(s\) under it had not yet been closed"
    ) as reported:
        async with DIContext(DIRegistry("app", [request_value])) as app_ctx:
            task = asyncio.create_task(request_task(app_ctx))
            await asyncio.sleep(0)
    assert "<DIContext [open] scope='request'" in str(reported.value)
    assert task is not None

    release.set()
    with pytest.raises(DIScopeError, match="was closed after its parent"):
        await task


async def test_child_left_open_in_unfinalised_generator_raises_at_parent() -> None:
    """A generator the consumer keeps never ends the block inside it, so the child never closes and
    could never report; the parent does."""

    @provide(scope="request")
    async def request_value() -> object:
        return object()

    async def stream(app_ctx: DIContext) -> AsyncGenerator[object, None]:
        async with app_ctx.enter_nested() as req:
            yield await req.solve("request_value")
            yield object()

    kept: list[AsyncGenerator[object, None]] = []
    with pytest.raises(DIScopeError, match=r"was closed while 1 nested context\(s\) under it had not yet been closed"):
        async with DIContext(DIRegistry("app", [request_value])) as app_ctx:
            agen = stream(app_ctx)
            await anext(agen)
            kept.append(agen)

    with pytest.raises(DIScopeError, match="was closed after its parent"):
        await kept[0].aclose()


async def test_unentered_child_closes_after_parent_without_error() -> None:
    app_ctx = DIContext(DIRegistry("app", []))
    await app_ctx.__aenter__()
    req = app_ctx.enter_nested()

    await app_ctx.__aexit__(None, None, None)
    await req.__aexit__(None, None, None)
    assert req.closed

    with pytest.raises(DIContextClosedError):
        await req.__aenter__()


async def test_entering_twice_raises() -> None:
    registry = DIRegistry("app", [])

    async with DIContext(registry) as ctx:
        with pytest.raises(DIScopeError, match="has already been entered"):
            async with ctx:
                pass

    with pytest.raises(DIContextClosedError):
        async with ctx:
            pass


async def test_using_closed_context_raises() -> None:
    registry = DIRegistry("app", [])
    ctx = DIContext(registry)
    await ctx.__aexit__(None, None, None)

    assert ctx.closed is True
    with pytest.raises(DIContextClosedError):
        await ctx.solve("anything")
    with pytest.raises(DIContextClosedError):
        await ctx.solve_many("anything")
    with pytest.raises(DIContextClosedError):
        ctx.get("anything")
    with pytest.raises(DIContextClosedError):
        await ctx.inject(lambda: None)
    with pytest.raises(DIContextClosedError):
        async with ctx.enter_nested():
            pass


async def test_production_finishing_after_close_raises_and_closes_resource() -> None:
    """Closing does not end a production in flight; opening the resource it comes back with raises,
    and the resource is closed again."""
    started = asyncio.Event()
    release = asyncio.Event()
    events: list[str] = []

    @provide(scope="app")
    async def slow() -> AsyncGenerator[str, None]:
        started.set()
        await release.wait()
        events.append("up")
        try:
            yield "value"
        finally:
            events.append("down")

    ctx = DIContext(DIRegistry("app", [slow]))
    await ctx.__aenter__()
    late = asyncio.create_task(ctx.solve("slow"))
    await started.wait()

    await ctx.__aexit__(None, None, None)
    assert events == []

    release.set()
    with pytest.raises(DIContextClosedError, match="Dependency 'slow' was closed again as soon as it was created"):
        await late

    # the resource was being created while the context was closing, so it is created and
    # closed again right away, to not leave an invalid state
    assert events == ["up", "down"]


async def test_solve_after_close_raises_without_calling_provider() -> None:
    events: list[str] = []

    @provide(scope="app")
    async def resource() -> AsyncGenerator[str, None]:
        events.append("up")
        try:
            yield "value"
        finally:
            events.append("down")

    ctx = DIContext(DIRegistry("app", [resource]))
    await ctx.__aexit__(None, None, None)

    with pytest.raises(DIContextClosedError, match="closed and can no longer resolve"):
        await ctx.solve("resource")
    assert events == []


async def test_close_during_production_tears_down_opened_dependency() -> None:
    """A dependency already opened is torn down even though the value using it never arrives."""
    entered = asyncio.Event()
    release = asyncio.Event()
    events: list[str] = []

    @provide(scope="app")
    async def resource() -> AsyncGenerator[str, None]:
        events.append("up")
        try:
            yield "value"
        finally:
            events.append("down")

    @provide(scope="app")
    async def slow(resource: NamedDependency[str]) -> str:
        entered.set()
        await release.wait()
        return resource

    ctx = DIContext(DIRegistry("app", [resource, slow]))
    await ctx.__aenter__()
    late = asyncio.create_task(ctx.solve("slow"))
    await entered.wait()
    assert events == ["up"]

    await ctx.__aexit__(None, None, None)
    assert events == ["up", "down"]

    release.set()
    with pytest.raises(DIContextClosedError, match="<DIContext.*was closed while resolving 'slow'"):
        await late


async def test_owner_closing_while_dependencies_resolve_raises_before_factory() -> None:
    """Resolving the dependencies suspends, and the owner can close meanwhile. The factory then
    does not run: its value could not be handed out. The dependency, whose owner is open, is kept."""
    entered = asyncio.Event()
    release = asyncio.Event()
    runs: list[str] = []

    @provide(scope="app")
    async def slow() -> str:
        entered.set()
        await release.wait()
        return "slow"

    @provide(scope="request")
    async def client(slow: NamedDependency[str]) -> str:
        runs.append("client")
        return slow

    async with DIContext(DIRegistry("app", [slow, client])) as app:
        request = app.enter_nested()
        await request.__aenter__()
        late = asyncio.create_task(request.solve("client"))
        await entered.wait()

        await request.__aexit__(None, None, None)
        release.set()
        with pytest.raises(DIContextClosedError, match="<DIContext.*was closed while resolving 'client'"):
            await late

        assert runs == []
        assert app.get("slow") == "slow"


async def test_inject_raises_without_calling_target_when_context_closes_meanwhile() -> None:
    called = False
    entered = asyncio.Event()
    release = asyncio.Event()

    @provide(scope="app")
    async def slow() -> str:
        entered.set()
        await release.wait()
        return "value"

    async def handler(slow: NamedDependency[str]) -> str:
        nonlocal called
        called = True
        return slow

    ctx = DIContext(DIRegistry("app", [slow]))
    await ctx.__aenter__()
    late = asyncio.create_task(ctx.inject(handler))
    await entered.wait()

    await ctx.__aexit__(None, None, None)
    release.set()

    with pytest.raises(DIContextClosedError, match="<DIContext.*was closed while resolving 'slow'"):
        await late
    assert called is False


async def test_app_production_completes_after_requesting_context_closes() -> None:
    """The value lives in the app context, which is open, so the production completes there and the
    next chain reads it; the closed request context was only the path it was asked through."""
    gate_started = asyncio.Event()
    release = asyncio.Event()
    productions = 0

    @provide(scope="app", key="gate")
    async def gate() -> str:
        gate_started.set()
        await release.wait()
        return "gate"

    @provide(scope="app", key="other")
    async def other() -> str:
        return "other"

    @provide(scope="app")
    async def combined(gate: NamedDependency[str], other: NamedDependency[str]) -> str:
        nonlocal productions
        productions += 1
        return f"{gate}+{other}"

    app_registry = DIRegistry("app", [])
    route = DIRegistry("route", [combined, gate, other])

    async with DIContext(app_registry) as app_ctx:
        async with DIContext(route, parent=app_ctx) as req:
            task = asyncio.create_task(req.solve("combined"))
            await gate_started.wait()
            await req.__aexit__(None, None, None)  # 'combined' still has 'other' left to resolve through ``req``
            release.set()
            assert await task == "gate+other"

        async with DIContext(route, parent=app_ctx) as req:
            assert await req.solve("combined") == "gate+other"

    assert productions == 1  # produced once, in the app context, and read by the second chain


async def test_resource_closed_again_with_failing_close_notes_why_it_was_closed() -> None:
    """The failure of the second close is what leaves, as a cleanup failure always is; the note
    keeps the fact that the resource was closed because the context had closed."""
    release = asyncio.Event()

    @provide(scope="app")
    async def resource() -> AsyncGenerator[str, None]:
        await release.wait()  # suspended inside ``__aenter__``, before the resource exists
        try:
            yield "value"
        finally:
            raise OSError("close failed")

    ctx = DIContext(DIRegistry("app", [resource]))
    await ctx.__aenter__()
    late = asyncio.create_task(ctx.solve("resource"))
    await asyncio.sleep(0)
    await ctx.__aexit__(None, None, None)

    release.set()
    with pytest.raises(OSError, match="close failed") as failed:
        await late
    assert any(
        note.startswith("Raised while closing 'resource'")
        and "its DIContext closed while the provider was being invoked" in note
        for note in failed.value.__notes__
    )


async def test_resolving_on_closed_context_raises_before_any_work_starts() -> None:
    """A walk over a factory's dependencies suspends while one of them is produced, and the
    requesting context can close in that gap. The next dependency it owns then raises before its
    factory runs: a resource opened now would have nothing left to tear it down."""
    entered = asyncio.Event()
    release = asyncio.Event()
    runs: list[str] = []

    @provide(scope="app")
    async def slow() -> str:
        entered.set()
        await release.wait()
        return "slow"

    @provide(scope="request")
    async def fast() -> str:
        runs.append("fast")
        return "fast"

    @provide(scope="request")
    async def client(slow: NamedDependency[str], fast: NamedDependency[str]) -> str:
        runs.append("client")
        return slow + fast

    async with DIContext(DIRegistry("app", [slow, fast, client])) as app:
        request = app.enter_nested()
        await request.__aenter__()
        late = asyncio.create_task(request.solve("client"))
        await entered.wait()

        await request.__aexit__(None, None, None)
        release.set()
        with pytest.raises(DIContextClosedError, match="closed and can no longer resolve"):
            await late

        assert runs == []  # 'fast' raised before its factory ran, 'client' was never reached
        assert app.get("slow") == "slow"  # the app-owned value the walk did produce is kept


async def test_resolving_parent_scoped_value_after_parent_closed_raises() -> None:
    """The owner is what matters: the value and its teardown would land there, not on the
    requester. A walk suspended in a request-owned dependency finds the app closed when it reaches
    an app-owned one, and raises there."""
    entered = asyncio.Event()
    release = asyncio.Event()
    runs: list[str] = []

    @provide(scope="request")
    async def slow() -> str:
        entered.set()
        await release.wait()
        return "slow"

    @provide(scope="app")
    async def shared() -> str:
        runs.append("shared")
        return "shared"

    @provide(scope="request")
    async def client(slow: NamedDependency[str], shared: NamedDependency[str]) -> str:
        return slow + shared

    app = DIContext(DIRegistry("app", [slow, shared, client]))
    await app.__aenter__()
    request = app.enter_nested()
    await request.__aenter__()
    late = asyncio.create_task(request.solve("client"))
    await entered.wait()

    with pytest.raises(
        DIScopeError, match=r".*was closed while 1 nested context\(s\) under it had not yet been closed"
    ):
        await app.__aexit__(None, None, None)  # out of order, by hand: the request stays open
    assert request.closed is False
    release.set()
    with pytest.raises(DIContextClosedError, match="closed and can no longer resolve") as exc_info:
        await late
    assert "scope='app'" in str(exc_info.value)
    assert runs == []

    with pytest.raises(DIScopeError, match="was closed after its parent"):
        await request.__aexit__(None, None, None)


async def test_waiter_released_after_close_raises_di_error_not_cancellation() -> None:
    """The waiter stays queued on the lock until the producer lets go (here by being cancelled by
    its own caller) and then finds a closed context; it is told so with a DI error, not with
    somebody else's cancellation"""
    started = asyncio.Event()

    @provide(scope="app")
    async def slow() -> str:
        started.set()
        await asyncio.Event().wait()  # never finishes on its own
        return "value"

    ctx = DIContext(DIRegistry("app", [slow]))
    await ctx.__aenter__()
    producer = asyncio.create_task(ctx.solve("slow"))
    await started.wait()
    waiter = asyncio.create_task(ctx.solve("slow"))
    await asyncio.sleep(0)

    await ctx.__aexit__(None, None, None)
    assert not waiter.done()  # still queued behind the producer, which the close does not own

    # The producer is still inside its provider. ending it is its own caller's business
    producer.cancel()
    with pytest.raises(DIContextClosedError):
        await waiter
    assert waiter.cancelled() is False
    await asyncio.gather(producer, return_exceptions=True)


async def test_close_does_not_wait_for_hanging_provider() -> None:

    @provide(scope="app")
    async def hangs() -> str:
        await asyncio.Event().wait()
        return "never"

    ctx = DIContext(DIRegistry("app", [hangs]))
    await ctx.__aenter__()
    caller = asyncio.create_task(ctx.solve("hangs"))
    await asyncio.sleep(0)

    await ctx.__aexit__(None, None, None)

    caller.cancel()
    await asyncio.gather(caller, return_exceptions=True)


async def test_unwound_cleanup_stack_raises_before_opening_resource() -> None:
    # a context checks that it is open before it uses its cleanup stack, so this check of
    # the stack cannot be reached through a context. the test calls the stack directly
    opened = False

    @provide(scope="app")
    async def resource() -> AsyncGenerator[str, None]:
        nonlocal opened
        opened = True
        yield "value"

    stack = _CleanupStack()
    await stack.aclose()

    with pytest.raises(DIContextClosedError, match="Cannot create 'resource' in closed DIContext"):
        await resource._produce({}, stack)

    assert opened is False


async def test_waiter_on_outer_scope_released_once_producer_lets_go() -> None:
    """One production waits on another in an outer scope; the waiter stays queued on the outer
    slot's lock until its producer lets go, and then finds its own context closed."""
    gate = asyncio.Event()

    @provide(scope="app")
    async def slow_app() -> str:
        await gate.wait()
        return "app"

    @provide(scope="request")
    async def req_value(slow_app: NamedDependency[str]) -> str:
        return f"req({slow_app})"

    registry = DIRegistry("app", [slow_app, req_value])
    app_ctx = DIContext(registry)
    await app_ctx.__aenter__()

    # One caller holds the lock of the app scoped slot and hangs inside the provider; another comes
    # through a request context and waits for that lock.
    producer = asyncio.create_task(app_ctx.solve("slow_app"))
    await asyncio.sleep(0)
    req = DIContext(registry, parent=app_ctx)
    await req.__aenter__()
    waiter = asyncio.create_task(req.solve("req_value"))
    await asyncio.sleep(0)
    assert slot_of(app_ctx, slow_app).running is True

    # Neither close waits for, or ends, the production the waiter is queued behind.
    await req.__aexit__(None, None, None)
    await app_ctx.__aexit__(None, None, None)
    assert not waiter.done()

    # The producer is still inside its provider; ending it is its own caller's business. Once it
    # lets go of the lock, the waiter's turn comes and it finds its context closed.
    producer.cancel()
    with pytest.raises(DIContextClosedError):
        await waiter
    await asyncio.gather(producer, return_exceptions=True)


async def test_cleanup_failure_raises_over_cancellation_during_teardown() -> None:
    """The failure leaves, with a note recording the cancellation. From 3.13 the cancellation is re-
    armed and lands at the caller's next await; before 3.13 it is let go and the caller carries on."""
    in_slow_cleanup = asyncio.Event()
    left: list[BaseException] = []

    @provide(scope="request")
    async def slow_close() -> AsyncGenerator[str, None]:
        try:
            yield "slow"
        finally:
            in_slow_cleanup.set()
            await asyncio.sleep(10)  # where the cancellation lands

    @provide(scope="request")
    async def bad_close(slow_close: NamedDependency[str]) -> AsyncGenerator[str, None]:
        yield "bad"
        raise ValueError("cleanup failed")

    async def body() -> str:
        async with DIContext(DIRegistry("app", [slow_close, bad_close])) as app:
            with pytest.raises(ValueError, match="cleanup failed") as exc_info:
                async with app.enter_nested() as request:
                    await request.solve("bad_close")
            left.append(exc_info.value)
            await asyncio.sleep(0)  # from 3.13 the re-armed cancellation lands here
            return "carried on"

    task = asyncio.create_task(body())
    await in_slow_cleanup.wait()
    task.cancel()

    if _IS_PY_313_PLUS:
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled()
    else:
        assert await task == "carried on"
        assert task.cancelled() is False
    assert any(note.startswith("Takes precedence over cancellation") for note in left[0].__notes__)


async def test_cleanup_failure_under_expired_timeout_leaves_no_stray_cancellation() -> None:
    """``asyncio.timeout`` uncancels the task on its way out; no ``CancelledError`` lands at the
    next await after the block, on any version."""

    @provide(scope="request")
    async def slow_close() -> AsyncGenerator[str, None]:
        try:
            yield "slow"
        finally:
            await asyncio.sleep(10)  # where the timeout expires

    @provide(scope="request")
    async def bad_close(slow_close: NamedDependency[str]) -> AsyncGenerator[str, None]:
        yield "bad"
        raise ValueError("cleanup failed")

    with pytest.raises(ValueError, match="cleanup failed") as exc_info:
        async with asyncio.timeout(0.02):
            async with DIContext(DIRegistry("app", [slow_close, bad_close])) as app, app.enter_nested() as request:
                await request.solve("bad_close")

    await asyncio.sleep(0)  # a stray cancellation would land here
    task = asyncio.current_task()
    assert task is not None and task.cancelling() == 0
    assert any(note.startswith("Takes precedence over cancellation") for note in exc_info.value.__notes__)


async def test_cancellation_during_teardown_finishes_teardown_and_re_raises() -> None:
    in_cleanup = asyncio.Event()
    torn_down: list[str] = []

    @provide(scope="request")
    async def first() -> AsyncGenerator[str, None]:
        try:
            yield "first"
        except BaseException as handed:
            torn_down.append(f"first, handed {type(handed).__name__}")
            raise

    @provide(scope="request")
    async def second(first: NamedDependency[str]) -> AsyncGenerator[str, None]:
        try:
            yield "second"
        finally:
            in_cleanup.set()
            await asyncio.sleep(10)  # where the cancellation lands
            torn_down.append("second")

    async def body() -> None:
        async with DIContext(DIRegistry("app", [first, second])) as app, app.enter_nested() as request:
            await request.solve("second")

    task = asyncio.create_task(body())
    await in_cleanup.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    # The cancellation interrupted ``second``'s cleanup; ``first`` was still closed, and was handed
    # the cancellation as the exception in flight, as it would be leaving nested ``async with``.
    assert torn_down == ["first, handed CancelledError"]
    assert task.cancelled()


async def test_cleanup_failure_raises_over_cleanup_raising_cancelled_error() -> None:
    """Nobody asked the task to cancel; the failure leaves and the caller carries on."""

    @provide(scope="request")
    async def self_cancelling() -> AsyncGenerator[str, None]:
        yield "x"
        raise asyncio.CancelledError

    @provide(scope="request")
    async def failing(self_cancelling: NamedDependency[str]) -> AsyncGenerator[str, None]:
        yield "y"
        raise ValueError("cleanup failed")

    async with DIContext(DIRegistry("app", [self_cancelling, failing])) as app:
        with pytest.raises(ValueError, match="cleanup failed"):
            async with app.enter_nested() as request:
                await request.solve("failing")
        await asyncio.sleep(0)

    task = asyncio.current_task()
    assert task is not None and task.cancelling() == 0


async def test_cancellation_inside_provider_tears_down_opened_resources_and_re_raises() -> None:
    """The resources the resolution opened are torn down, most recent first, and the cancellation
    leaves as it is."""
    in_factory = asyncio.Event()
    torn_down: list[str] = []

    @provide(scope="app")
    async def first() -> AsyncGenerator[str, None]:
        try:
            yield "first"
        finally:
            torn_down.append("first")

    @provide(scope="app")
    async def second(first: NamedDependency[str]) -> AsyncGenerator[str, None]:
        try:
            yield "second"
        finally:
            torn_down.append("second")

    @provide(scope="app")
    async def top(second: NamedDependency[str]) -> str:
        in_factory.set()
        await asyncio.sleep(10)  # where the cancellation lands
        return "top"

    async def body() -> str:
        async with DIContext(DIRegistry("app", [first, second, top])) as ctx:
            return await ctx.solve("top")  # type: ignore[no-any-return]

    task = asyncio.create_task(body())
    await in_factory.wait()
    task.cancel()

    with pytest.raises(asyncio.CancelledError):
        await task
    assert task.cancelled()
    assert torn_down == ["second", "first"]


async def test_foreign_cancellation_inside_provider_tears_down_opened_resources_and_re_raises() -> None:
    """A future somebody else cancels delivers ``CancelledError`` into the provider although nobody
    cancelled the caller: the resources opened are torn down, most recent first, and the caller,
    never cancelled, gets it as it is."""
    torn_down: list[str] = []

    @provide(scope="app")
    async def first() -> AsyncGenerator[str, None]:
        try:
            yield "first"
        finally:
            torn_down.append("first")

    @provide(scope="app")
    async def second(first: NamedDependency[str]) -> AsyncGenerator[str, None]:
        try:
            yield "second"
        finally:
            torn_down.append("second")

    @provide(scope="app")
    async def top(second: NamedDependency[str]) -> str:
        somebody_elses = asyncio.get_running_loop().create_future()
        asyncio.get_running_loop().call_soon(somebody_elses.cancel)
        await somebody_elses
        return "top"

    with pytest.raises(asyncio.CancelledError):
        async with DIContext(DIRegistry("app", [first, second, top])) as ctx:
            await ctx.solve("top")

    assert torn_down == ["second", "first"]
    task = asyncio.current_task()
    assert task is not None and task.cancelling() == 0


async def test_cancellation_inside_request_provider_tears_down_request_only() -> None:
    """The cancellation leaves through the request context's teardown and past the app context:
    the request's resources are torn down at once, the app's when the app closes.
    """
    opened = 0
    torn_down: list[str] = []

    @provide(scope="app")
    async def engine() -> AsyncGenerator[str, None]:
        nonlocal opened
        opened += 1
        try:
            yield "engine"
        finally:
            torn_down.append("engine")

    @provide(scope="request")
    async def session(engine: NamedDependency[str]) -> AsyncGenerator[str, None]:
        try:
            yield "session"
        finally:
            torn_down.append("session")

    @provide(scope="request")
    async def handler_value(session: NamedDependency[str]) -> str:
        somebody_elses = asyncio.get_running_loop().create_future()
        asyncio.get_running_loop().call_soon(somebody_elses.cancel)
        await somebody_elses
        return "value"

    async with DIContext(DIRegistry("app", [engine, session, handler_value])) as app:
        with pytest.raises(asyncio.CancelledError):
            async with app.enter_nested() as request:
                await request.solve("handler_value")
        assert torn_down == ["session"]
        assert await app.solve("engine") == "engine"
        assert opened == 1

    assert torn_down == ["session", "engine"]


async def test_cleanup_failing_after_cancellation_raises_failure() -> None:
    # a cleanup that runs after the cancellation landed is handed the cancellation, not
    # the original exception. when that cleanup fails, its failure is what gets raised
    in_slow_cleanup = asyncio.Event()
    handed: list[str] = []

    @provide(scope="request")
    async def bad_close() -> AsyncGenerator[str, None]:
        try:
            yield "bad"
        except BaseException as exc:
            handed.append(type(exc).__name__)
            raise ValueError("cleanup failed") from None

    @provide(scope="request")
    async def slow_close(bad_close: NamedDependency[str]) -> AsyncGenerator[str, None]:
        try:
            yield "slow"
        finally:
            in_slow_cleanup.set()
            await asyncio.sleep(10)  # where the cancellation lands

    async def body() -> None:
        async with DIContext(DIRegistry("app", [bad_close, slow_close])) as app, app.enter_nested() as request:
            await request.solve("slow_close")
            raise RuntimeError("body failed")

    task = asyncio.create_task(body())
    await in_slow_cleanup.wait()
    task.cancel()

    with pytest.raises(ValueError, match="cleanup failed") as exc_info:
        await task
    assert handed == ["CancelledError"]
    assert any(note.startswith("Takes precedence over cancellation") for note in exc_info.value.__notes__)
    assert task.cancelled() is False


async def test_cancellation_during_teardown_noted_on_exception_group() -> None:
    in_slow_cleanup = asyncio.Event()

    @provide(scope="request")
    async def slow_close() -> AsyncGenerator[str, None]:
        try:
            yield "slow"
        finally:
            in_slow_cleanup.set()
            await asyncio.sleep(10)  # where the cancellation lands

    @provide(scope="request")
    async def bad_one(slow_close: NamedDependency[str]) -> AsyncGenerator[str, None]:
        yield "one"
        raise ValueError("one failed")

    @provide(scope="request")
    async def bad_two(bad_one: NamedDependency[str]) -> AsyncGenerator[str, None]:
        yield "two"
        raise ValueError("two failed")

    async def body() -> None:
        async with DIContext(DIRegistry("app", [slow_close, bad_one, bad_two])) as app, app.enter_nested() as request:
            await request.solve("bad_two")

    task = asyncio.create_task(body())
    await in_slow_cleanup.wait()
    task.cancel()

    with pytest.raises(BaseExceptionGroup) as exc_info:
        await task
    assert {str(failure) for failure in exc_info.value.exceptions} == {"one failed", "two failed"}
    assert any(note.startswith("Takes precedence over cancellation") for note in exc_info.value.__notes__)
    assert task.cancelled() is False


async def test_foreign_cancellation_during_teardown_not_re_armed() -> None:

    @provide(scope="request")
    async def bad_close() -> AsyncGenerator[str, None]:
        try:
            yield "bad"
        finally:
            raise ValueError("cleanup failed")

    @provide(scope="request")
    async def foreign_close(bad_close: NamedDependency[str]) -> AsyncGenerator[str, None]:
        try:
            yield "foreign"
        finally:
            somebody_elses = asyncio.get_running_loop().create_future()
            asyncio.get_running_loop().call_soon(somebody_elses.cancel)
            await somebody_elses

    with pytest.raises(ValueError, match="cleanup failed") as exc_info:
        async with DIContext(DIRegistry("app", [bad_close, foreign_close])) as app, app.enter_nested() as request:
            await request.solve("foreign_close")

    assert any(note.startswith("Takes precedence over cancellation") for note in exc_info.value.__notes__)
    await asyncio.sleep(0)  # a re-armed cancellation would land here
    task = asyncio.current_task()
    assert task is not None and task.cancelling() == 0


async def test_cleanup_failure_raises_over_body_cancellation_and_keeps_it() -> None:
    """The task was cancelled in the body, so the block is leaving with the cancellation when a
    cleanup fails. The failure is what leaves, with a note; from 3.13 the cancellation is re-armed
    and lands at the next await, before 3.13 it is let go."""
    in_body = asyncio.Event()
    left: list[BaseException] = []

    @provide(scope="request")
    async def bad_close() -> AsyncGenerator[str, None]:
        try:
            yield "bad"
        finally:
            raise ValueError("cleanup failed")

    async def body() -> str:
        async with DIContext(DIRegistry("app", [bad_close])) as app:
            with pytest.raises(ValueError, match="cleanup failed") as exc_info:
                async with app.enter_nested() as request:
                    await request.solve("bad_close")
                    in_body.set()
                    await asyncio.sleep(10)  # where the cancellation lands
            left.append(exc_info.value)
            await asyncio.sleep(0)  # from 3.13 the re-armed cancellation lands here
            return "carried on"

    task = asyncio.create_task(body())
    await in_body.wait()
    task.cancel()

    if _IS_PY_313_PLUS:
        with pytest.raises(asyncio.CancelledError):
            await task
        assert task.cancelled()
    else:
        assert await task == "carried on"
        assert task.cancelled() is False
    assert "Takes precedence over a cancellation of the cleanup task" in left[0].__notes__


async def test_cancellation_during_sync_generator_cleanup_raised_after_cleanup() -> None:
    events: list[str] = []
    committing = threading.Event()
    commit = threading.Event()

    @provide(scope="app")
    def connection() -> Generator[str, None, None]:
        try:
            yield "connection"
        finally:
            events.append("connection closed")

    @provide(scope="app")
    def transaction(connection: NamedDependency[str]) -> Generator[str, None, None]:
        yield "transaction"
        committing.set()
        commit.wait(2)
        events.append("committed")

    async def use() -> None:
        async with DIContext(DIRegistry("app", [connection, transaction])) as ctx:
            await ctx.solve("transaction")

    task = asyncio.create_task(use())
    await asyncio.to_thread(committing.wait, 2)
    task.cancel()
    await asyncio.sleep(0.01)
    assert events == []

    commit.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert events == ["committed", "connection closed"]


async def test_cancellation_during_sync_generator_setup_thrown_into_generator() -> None:
    events: list[str] = []
    setting_up = threading.Event()
    finish_setup = threading.Event()

    @provide(scope="app")
    def resource() -> Generator[str, None, None]:
        setting_up.set()
        finish_setup.wait(2)
        try:
            yield "value"
        except asyncio.CancelledError:
            events.append("cancellation thrown in")
            raise

    async with DIContext(DIRegistry("app", [resource])) as ctx:
        task = asyncio.create_task(ctx.solve("resource"))
        await asyncio.to_thread(setting_up.wait, 2)
        task.cancel()
        await asyncio.sleep(0.01)
        assert not task.done()

        finish_setup.set()
        with pytest.raises(asyncio.CancelledError):
            await task

    assert events == ["cancellation thrown in"]


async def test_cancellation_during_failing_sync_generator_setup_raises_cancellation() -> None:
    setting_up = threading.Event()
    finish_setup = threading.Event()

    @provide(scope="app")
    def resource() -> Generator[str, None, None]:
        setting_up.set()
        finish_setup.wait(2)
        raise ValueError
        yield "value"  # type: ignore[unreachable]

    async with DIContext(DIRegistry("app", [resource])) as ctx:
        task = asyncio.create_task(ctx.solve("resource"))
        await asyncio.to_thread(setting_up.wait, 2)
        task.cancel()
        finish_setup.set()

        with pytest.raises(asyncio.CancelledError):
            await task


async def test_wait_for_sync_generator_cleanup_shielded_in_cancelled_anyio_scope() -> None:
    # performance: anyio cancels a task of a cancelled scope again on every pass of the event loop. the
    # wait for the generator's thread is shielded, so the task is not woken on each of them
    cancellations = 0

    class CountingTask(asyncio.Task[None]):
        def cancel(self, msg: Any = None) -> bool:
            nonlocal cancellations
            cancellations += 1
            return super().cancel(msg)

    events: list[str] = []
    in_use = asyncio.Event()
    cleaning_up = threading.Event()
    finish_cleanup = threading.Event()

    @provide(scope="app")
    def resource() -> Generator[str, None, None]:
        try:
            yield "value"
        finally:
            cleaning_up.set()
            finish_cleanup.wait(2)
            events.append("cleaned up")

    scope = anyio.CancelScope()

    async def use() -> None:
        with scope:
            async with DIContext(DIRegistry("app", [resource])) as ctx:
                await ctx.solve("resource")
                in_use.set()
                await asyncio.sleep(10)
        events.append("left the scope")

    task = CountingTask(use())
    await in_use.wait()
    scope.cancel()
    await asyncio.to_thread(cleaning_up.wait, 2)
    await asyncio.sleep(0.05)
    finish_cleanup.set()
    await task

    assert events == ["cleaned up", "left the scope"]
    assert cancellations < 10


async def test_wait_for_sync_generator_setup_shielded_in_cancelled_anyio_scope() -> None:
    # performance: anyio cancels a task of a cancelled scope again on every pass of the event loop. the
    # wait for the generator's thread is shielded, so the task is not woken on each of them
    cancellations = 0

    class CountingTask(asyncio.Task[None]):
        def cancel(self, msg: Any = None) -> bool:
            nonlocal cancellations
            cancellations += 1
            return super().cancel(msg)

    events: list[str] = []
    setting_up = threading.Event()
    finish_setup = threading.Event()

    @provide(scope="app")
    def resource() -> Generator[str, None, None]:
        setting_up.set()
        finish_setup.wait(2)
        try:
            yield "value"
        except asyncio.CancelledError:
            events.append("cancellation thrown in")
            raise

    scope = anyio.CancelScope()

    async def use() -> None:
        with scope:
            async with DIContext(DIRegistry("app", [resource])) as ctx:
                await ctx.solve("resource")
        events.append("left the scope")

    task = CountingTask(use())
    await asyncio.to_thread(setting_up.wait, 2)
    scope.cancel()
    await asyncio.sleep(0.05)
    finish_setup.set()
    await task

    assert events == ["cancellation thrown in", "left the scope"]
    assert cancellations < 10
