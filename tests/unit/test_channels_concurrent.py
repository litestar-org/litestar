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
