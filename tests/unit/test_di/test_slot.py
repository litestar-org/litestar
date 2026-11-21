# pyright: reportUnnecessaryTypeIgnoreComment=false
from __future__ import annotations

import asyncio

from litestar.di import DIContext, provide
from litestar.di.context import _ProviderSlot
from tests.unit.test_di.helpers import registry_with_providers, slot_of


async def test_slot_repr_reflects_state() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    @provide(scope="app")
    async def slow() -> int:
        started.set()
        await release.wait()
        return 1

    async with DIContext(registry_with_providers(slow)) as ctx:
        slot = slot_of(ctx, slow)
        assert repr(slot) == f"<_ProviderSlot [empty] provider={slow!r} at {id(slot):#x}>"

        task = asyncio.create_task(ctx.solve("slow"))
        await started.wait()
        assert repr(slot) == f"<_ProviderSlot [producing] provider={slow!r} at {id(slot):#x}>"

        release.set()
        await task
        assert repr(slot) == f"<_ProviderSlot [resolved] provider={slow!r} value=1 at {id(slot):#x}>"


async def test_slot_repr_truncates_value_repr() -> None:
    @provide(scope="app")
    async def numbers() -> list[int]:
        return list(range(10_000))

    async with DIContext(registry_with_providers(numbers)) as ctx:
        await ctx.solve("numbers")
        assert "value=[0, 1, 2, 3, 4, 5, ...] at" in repr(slot_of(ctx, numbers))


async def test_set_result() -> None:
    @provide(scope="app")
    async def value() -> int:
        return 1

    slot = _ProviderSlot(value)

    slot.set_result(42)

    assert slot.done is True
    assert slot.running is False
    assert slot.value == 42


async def test_running_state_production() -> None:
    # should be 'True' during the production
    started = asyncio.Event()
    release = asyncio.Event()

    @provide(scope="app")
    async def slow() -> int:
        started.set()
        await release.wait()
        return 1

    async with DIContext(registry_with_providers(slow)) as ctx:
        slot = slot_of(ctx, slow)
        assert slot.running is False

        task = asyncio.create_task(ctx.solve("slow"))
        await started.wait()
        assert slot.running is True
        assert slot.done is False  # type: ignore[unreachable]
        assert slot._lock is not None and slot._lock.locked()

        release.set()
        await task
        assert slot.done is True
        assert slot.running is False
        assert not slot._lock.locked()
