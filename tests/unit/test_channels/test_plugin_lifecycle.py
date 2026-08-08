from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import AsyncMock

import pytest

from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.channels.plugin import ChannelsException


class _DisconnectingSocket:
    def __init__(self, operations: list[str]) -> None:
        self.operations = operations

    async def accept(self) -> None:
        self.operations.append("accept")

    async def send_text(self, data: bytes) -> None:
        return None

    async def send_bytes(self, data: bytes) -> None:
        return None

    async def receive(self) -> dict[str, Any]:
        return {"type": "websocket.disconnect"}


async def test_subscribe_validates_generator_before_mutating_state() -> None:
    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock()
    plugin = ChannelsPlugin(backend=backend, channels=["known"])

    with pytest.raises(ChannelsException):
        await plugin.subscribe(channel for channel in ["known", "unknown"])

    assert not plugin._channels["known"]
    backend.subscribe.assert_not_awaited()


async def test_subscribe_rolls_back_dynamic_channel_on_backend_error() -> None:
    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock(side_effect=RuntimeError("subscribe failed"))
    backend.unsubscribe = AsyncMock()
    plugin = ChannelsPlugin(backend=backend, arbitrary_channels_allowed=True)

    with pytest.raises(RuntimeError, match="subscribe failed"):
        await plugin.subscribe("dynamic")

    assert "dynamic" not in plugin._channels
    backend.unsubscribe.assert_awaited_once_with({"dynamic"})


async def test_unsubscribe_prunes_only_dynamic_channels_and_is_idempotent() -> None:
    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock()
    backend.unsubscribe = AsyncMock()
    plugin = ChannelsPlugin(backend=backend, channels=["configured"], arbitrary_channels_allowed=True)
    subscriber = await plugin.subscribe(["configured", "dynamic"])

    await plugin.unsubscribe(subscriber)
    await plugin.unsubscribe(subscriber)

    assert "configured" in plugin._channels
    assert "dynamic" not in plugin._channels
    backend.unsubscribe.assert_awaited_once_with({"configured", "dynamic"})


async def test_unsubscribe_restores_subscriber_on_backend_error() -> None:
    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock()
    backend.unsubscribe = AsyncMock(side_effect=RuntimeError("unsubscribe failed"))
    plugin = ChannelsPlugin(backend=backend, channels=["configured"])
    subscriber = await plugin.subscribe("configured")

    with pytest.raises(RuntimeError, match="unsubscribe failed"):
        await plugin.unsubscribe(subscriber, "configured")

    assert subscriber in plugin._channels["configured"]


async def test_start_subscription_materializes_generator_for_cleanup() -> None:
    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock()
    backend.unsubscribe = AsyncMock()
    plugin = ChannelsPlugin(backend=backend, arbitrary_channels_allowed=True)

    async with plugin.start_subscription(channel for channel in ["dynamic"]):
        assert "dynamic" in plugin._channels

    assert "dynamic" not in plugin._channels
    backend.unsubscribe.assert_awaited_once_with({"dynamic"})


async def test_concurrent_first_subscriptions_use_one_backend_transition() -> None:
    entered = asyncio.Event()
    release = asyncio.Event()

    async def subscribe_backend(channels: set[str]) -> None:
        entered.set()
        await release.wait()

    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock(side_effect=subscribe_backend)
    plugin = ChannelsPlugin(backend=backend, arbitrary_channels_allowed=True)

    first = asyncio.create_task(plugin.subscribe("shared"))
    await entered.wait()
    second = asyncio.create_task(plugin.subscribe("shared"))
    await asyncio.sleep(0)
    release.set()
    await asyncio.gather(first, second)

    backend.subscribe.assert_awaited_once_with({"shared"})


async def test_last_unsubscribe_finishes_before_new_first_subscribe() -> None:
    unsubscribe_started = asyncio.Event()
    release_unsubscribe = asyncio.Event()

    async def unsubscribe_backend(channels: set[str]) -> None:
        unsubscribe_started.set()
        await release_unsubscribe.wait()

    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock()
    backend.unsubscribe = AsyncMock(side_effect=unsubscribe_backend)
    plugin = ChannelsPlugin(backend=backend, arbitrary_channels_allowed=True)
    original = await plugin.subscribe("shared")
    backend.subscribe.reset_mock()

    unsubscribe = asyncio.create_task(plugin.unsubscribe(original, "shared"))
    await unsubscribe_started.wait()
    subscribe = asyncio.create_task(plugin.subscribe("shared"))
    await asyncio.sleep(0)

    assert not subscribe.done()
    release_unsubscribe.set()
    _, replacement = await asyncio.gather(unsubscribe, subscribe)

    assert replacement in plugin._channels["shared"]
    backend.subscribe.assert_awaited_once_with({"shared"})


async def test_history_error_is_not_masked_by_cleanup_error() -> None:
    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock()
    backend.unsubscribe = AsyncMock(side_effect=RuntimeError("cleanup failed"))
    backend.get_history = AsyncMock(side_effect=LookupError("history failed"))
    plugin = ChannelsPlugin(backend=backend, arbitrary_channels_allowed=True)

    with pytest.raises(LookupError, match="history failed"):
        await plugin.subscribe("dynamic", history=1)


async def test_cancelled_backend_subscription_cleans_up() -> None:
    entered = asyncio.Event()

    async def subscribe_backend(channels: set[str]) -> None:
        entered.set()
        await asyncio.Event().wait()

    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock(side_effect=subscribe_backend)
    backend.unsubscribe = AsyncMock()
    plugin = ChannelsPlugin(backend=backend, arbitrary_channels_allowed=True)
    subscription = asyncio.create_task(plugin.subscribe("dynamic"))
    await entered.wait()

    subscription.cancel()
    with pytest.raises(asyncio.CancelledError):
        await subscription

    assert "dynamic" not in plugin._channels


async def test_websocket_accepts_after_subscription_and_history() -> None:
    operations: list[str] = []

    async def subscribe_backend(channels: set[str]) -> None:
        operations.append("subscribe")

    async def get_history(channel: str, limit: int | None) -> list[bytes]:
        operations.append("history")
        return []

    backend = MemoryChannelsBackend()
    backend.subscribe = AsyncMock(side_effect=subscribe_backend)
    backend.unsubscribe = AsyncMock()
    backend.get_history = AsyncMock(side_effect=get_history)
    plugin = ChannelsPlugin(backend=backend, arbitrary_channels_allowed=True, ws_handler_send_history=1)

    await plugin._ws_handler_func("dynamic", _DisconnectingSocket(operations))  # type: ignore[arg-type]

    assert operations == ["subscribe", "history", "accept"]
