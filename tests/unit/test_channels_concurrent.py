from __future__ import annotations

import asyncio
from asyncio import Event
from collections.abc import Iterable

import pytest
from anyio import fail_after

from litestar.channels import ChannelsPlugin
from litestar.channels.backends.memory import MemoryChannelsBackend


class StubMemoryChannelBackend(MemoryChannelsBackend):
    """Backend that introduces artificial lag in unsubscribe() to widen the race window."""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._lag_event = Event()
        self._continue_event = Event()

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        self._lag_event.set()
        await self._continue_event.wait()
        return await super().unsubscribe(channels)


@pytest.mark.asyncio
async def test_concurrent_subscribe_unsubscribe_does_not_lose_events() -> None:
    """Regression test for #4894.

    Concurrent subscribe and unsubscribe of the last subscriber for the same
    channel must not cause the backend to unsubscribe while a new subscriber
    is being added, which would result in silent event loss.
    """
    backend = StubMemoryChannelBackend()
    channels = ChannelsPlugin(arbitrary_channels_allowed=True, backend=backend)

    async def concurrent_subscribe() -> None:
        # Wait until unsubscribe() is in progress
        await backend._lag_event.wait()
        backend._continue_event.set()
        subscriber = await channels.subscribe("42")
        await channels.wait_published("42", "42")
        try:
            with fail_after(1):
                await anext(subscriber.iter_events())
        except TimeoutError as e:
            raise ValueError("Expected event not received") from e

    async with channels:
        first_subscriber = await channels.subscribe("42")
        await asyncio.gather(
            concurrent_subscribe(),
            channels.unsubscribe(first_subscriber, "42"),
        )


@pytest.mark.asyncio
async def test_unsubscribe_cleans_empty_channel_entries() -> None:
    """Regression test for #4867.

    unsubscribe() must delete the channel key from self._channels when
    the last subscriber leaves, otherwise arbitrary_channels_allowed
    causes unbounded memory growth.
    """
    plugin = ChannelsPlugin(backend=MemoryChannelsBackend(history=10), arbitrary_channels_allowed=True)
    async with plugin:
        for i in range(100):
            channel = f"user_{i}"
            subscriber = await plugin.subscribe([channel])
            await plugin.unsubscribe(subscriber, [channel])

    assert len(plugin._channels) == 0, f"Expected 0, got {len(plugin._channels)}"


@pytest.mark.asyncio
async def test_subscribe_cancellation_does_not_leak_subscriber() -> None:
    """Regression test for #4871.

    If subscribe() is cancelled during a blocking history fetch, the
    subscriber must not be leaked into self._channels.
    """
    barrier = asyncio.Event()
    release = asyncio.Event()

    class SlowHistoryBackend(MemoryChannelsBackend):
        def __init__(self, history: int = 1) -> None:
            super().__init__(history=history)
            self._barrier = barrier
            self._release = release

        async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
            self._barrier.set()
            await self._release.wait()
            return await super().get_history(channel, limit)

    backend = SlowHistoryBackend(history=1)
    plugin = ChannelsPlugin(backend=backend, arbitrary_channels_allowed=True)
    channel = "user:1"

    async with plugin:
        task = asyncio.create_task(plugin.subscribe([channel], history=1))
        await barrier.wait()

        registered_before = len(plugin._channels.get(channel, set()))

        task.cancel()
        await asyncio.gather(task, return_exceptions=True)

        leaked = len(plugin._channels.get(channel, set()))

        assert registered_before == 0, (
            f"Subscriber should not be registered while still awaiting: got {registered_before}"
        )
        assert leaked == 0, f"Subscriber leaked into _channels after cancel: got {leaked}"
