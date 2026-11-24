from __future__ import annotations

import asyncio
from collections.abc import AsyncGenerator
from typing import Any

import pytest

from litestar.di import DIContext, DIRegistry, NamedDependency, Provider, provide

LEAF_COUNT = 40
CHAIN_DEPTH = 60


def build_wide_graph(counters: dict[str, int]) -> DIRegistry:
    """one root depending on LEAF_COUNT independent leaves"""
    providers: list[Provider] = []

    def make_leaf(index: int) -> Provider:
        async def leaf() -> int:
            counters[f"leaf{index}"] = counters.get(f"leaf{index}", 0) + 1
            await asyncio.sleep(0)
            return index

        return Provider(leaf, kind="named", scope="request", key=f"leaf{index}")

    providers.extend(make_leaf(index) for index in range(LEAF_COUNT))

    namespace: dict[str, Any] = {"__name__": __name__, "NamedDependency": NamedDependency, "counters": counters}
    parameters = ", ".join(f"leaf{index}: NamedDependency[int]" for index in range(LEAF_COUNT))
    body = " + ".join(f"leaf{index}" for index in range(LEAF_COUNT))
    exec(
        f"async def root({parameters}) -> int:\n"
        f"    counters['root'] = counters.get('root', 0) + 1\n"
        f"    return {body}\n",
        namespace,
    )
    providers.append(Provider(namespace["root"], kind="named", scope="request"))
    return DIRegistry("app", providers)


def build_deep_chain(counters: dict[str, int]) -> DIRegistry:
    """level0 <- level1 <- ... <- level{CHAIN_DEPTH - 1}"""
    namespace: dict[str, Any] = {"__name__": __name__, "NamedDependency": NamedDependency, "counters": counters}
    source = ["async def level0() -> int:", "    counters['level0'] = counters.get('level0', 0) + 1", "    return 0"]
    for level in range(1, CHAIN_DEPTH):
        source += [
            f"async def level{level}(level{level - 1}: NamedDependency[int]) -> int:",
            f"    counters['level{level}'] = counters.get('level{level}', 0) + 1",
            f"    return level{level - 1} + 1",
        ]
    exec("\n".join(source), namespace)

    return DIRegistry(
        "app",
        [Provider(namespace[f"level{level}"], kind="named", scope="request") for level in range(CHAIN_DEPTH)],
    )


async def test_wide_fan_out_resolves_every_leaf_exactly_once() -> None:
    counters: dict[str, int] = {}
    registry = build_wide_graph(counters)

    async with DIContext(registry) as app_ctx, app_ctx.enter_nested() as req:
        results = await asyncio.gather(*(req.solve("root") for _ in range(25)))

    assert set(results) == {sum(range(LEAF_COUNT))}
    assert counters["root"] == 1
    assert all(counters[f"leaf{index}"] == 1 for index in range(LEAF_COUNT))


async def test_deep_chain_resolves_each_level_once() -> None:
    counters: dict[str, int] = {}
    registry = build_deep_chain(counters)

    async with DIContext(registry) as app_ctx, app_ctx.enter_nested() as req:
        assert await req.solve(f"level{CHAIN_DEPTH - 1}") == CHAIN_DEPTH - 1

    assert all(count == 1 for count in counters.values())


async def test_concurrent_requests_do_not_share_request_scoped_values() -> None:
    counters: dict[str, int] = {}

    @provide(scope="app")
    async def shared() -> object:
        counters["shared"] = counters.get("shared", 0) + 1
        await asyncio.sleep(0)
        return object()

    @provide(scope="request")
    async def per_request(shared: NamedDependency[object]) -> object:
        counters["per_request"] = counters.get("per_request", 0) + 1
        await asyncio.sleep(0)
        return object()

    registry = DIRegistry("app", [shared, per_request])

    async def one_request(app_ctx: DIContext) -> tuple[object, object]:
        async with app_ctx.enter_nested() as req:
            return await req.solve("shared"), await req.solve("per_request")

    async with DIContext(registry) as app_ctx:
        results = await asyncio.gather(*(one_request(app_ctx) for _ in range(30)))

    shared_values = {id(shared_value) for shared_value, _ in results}
    request_values = {id(request_value) for _, request_value in results}

    assert len(shared_values) == 1
    assert len(request_values) == 30
    assert counters["shared"] == 1
    assert counters["per_request"] == 30


async def test_cancelling_request_does_not_affect_siblings() -> None:
    gate = asyncio.Event()
    torn_down: list[int] = []

    opened: list[int] = []

    @provide(scope="request")
    async def resource() -> AsyncGenerator[int, None]:
        index = len(opened)
        opened.append(index)
        # ``try``/``finally`` because the cancelled request throws CancelledError into
        # this generator at the yield; code after a bare yield would be skipped, as it
        # would be in any other context manager
        try:
            yield index
        finally:
            torn_down.append(index)

    @provide(scope="app")
    async def slow() -> str:
        await gate.wait()
        return "slow"

    registry = DIRegistry("app", [resource, slow])

    resource_ready = asyncio.Event()

    async def one_request(app_ctx: DIContext, *, wait_for_slow: bool) -> str:
        async with app_ctx.enter_nested() as req:
            await req.solve("resource")
            resource_ready.set()
            if wait_for_slow:
                await req.solve("slow")
            return "done"

    async with DIContext(registry) as app_ctx:
        cancelled = asyncio.create_task(one_request(app_ctx, wait_for_slow=True))
        # cancel only once the request actually holds an open resource, so the assertion below is
        # about teardown rather than about how far the task happened to get
        await resource_ready.wait()
        cancelled.cancel()
        with pytest.raises(asyncio.CancelledError):
            await cancelled

        gate.set()
        assert await one_request(app_ctx, wait_for_slow=True) == "done"

    # the cancelled request still tore its own resource down
    assert len(torn_down) == 2


async def test_solve_and_inject_interleave_safely() -> None:
    counters: dict[str, int] = {}

    @provide(scope="request")
    async def value() -> int:
        counters["value"] = counters.get("value", 0) + 1
        await asyncio.sleep(0)
        return 1

    async def handler(value: NamedDependency[int]) -> int:
        return value

    registry = DIRegistry("app", [value])
    async with DIContext(registry) as app_ctx, app_ctx.enter_nested() as req:
        mixed = await asyncio.gather(
            req.solve("value"),
            req.inject(handler),
            req.solve("value"),
            req.inject(handler),
        )

    assert list(mixed) == [1, 1, 1, 1]
    assert counters["value"] == 1


async def test_concurrent_callers_racing_for_one_slot_get_one_value() -> None:
    """
    Two hundred requests, each through a request context of its own, race to create the
    app context's slot. We expect one production and one slot in the end
    """
    calls = 0

    @provide(scope="app")
    async def shared() -> int:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return calls

    registry = DIRegistry("app", [shared])
    async with DIContext(registry) as app_ctx:
        assert app_ctx._slots == {}

        # every caller comes through a request context of its own, so none of them can
        # be handed the slot by a parent that already made it
        async def one_request() -> int:
            async with DIContext(registry, scope="request", parent=app_ctx) as req:
                return int(await req.solve("shared"))

        results = await asyncio.gather(*(one_request() for _ in range(200)))

        assert results == [1] * 200
        assert calls == 1
        assert len(app_ctx._slots) == 1
