from __future__ import annotations

import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest

from litestar.channels import Subscriber
from litestar.channels.backends.memory import MemoryChannelsBackend
from litestar.channels.plugin import ChannelsPlugin


def test_subscriber_backlog_backoff() -> None:
    subscriber = Subscriber(plugin=MagicMock(), max_backlog=2, backlog_strategy="backoff")

    assert subscriber.put_nowait(b"foo")
    assert subscriber.put_nowait(b"bar")
    assert not subscriber.put_nowait(b"baz")

    assert subscriber.qsize == 2
    assert [subscriber._queue.get_nowait(), subscriber._queue.get_nowait()] == [b"foo", b"bar"]


def test_subscriber_backlog_dropleft() -> None:
    subscriber = Subscriber(plugin=MagicMock(), max_backlog=2, backlog_strategy="dropleft")

    assert subscriber.put_nowait(b"foo")
    assert subscriber.put_nowait(b"bar")
    assert subscriber.put_nowait(b"baz")

    assert subscriber.qsize == 2
    assert [subscriber._queue.get_nowait(), subscriber._queue.get_nowait()] == [b"bar", b"baz"]


async def test_iter_events_none_breaks() -> None:
    subscriber = Subscriber(MagicMock())
    mock_callback = MagicMock()

    subscriber.put_nowait(b"foo")
    subscriber.put_nowait(None)

    async def consume() -> None:
        async for event in subscriber.iter_events():
            mock_callback(event)

    await asyncio.wait_for(consume(), timeout=0.1)

    mock_callback.assert_called_once_with(b"foo")


@pytest.fixture()
async def plugin() -> AsyncGenerator[ChannelsPlugin, None]:
    memory_backend = MemoryChannelsBackend(history=10)
    plugin = ChannelsPlugin(backend=memory_backend, arbitrary_channels_allowed=True)
    await plugin._on_startup()
    yield plugin
    await plugin._on_shutdown()


@pytest.mark.parametrize("channels,expected_entries", [("foo", 1), (["foo", "bar"], 2)])
async def test_put_history(channels: str | list[str], plugin: ChannelsPlugin, expected_entries: int) -> None:
    subscriber = Subscriber(plugin)
    await plugin._backend.publish(b"something", channels if isinstance(channels, list) else [channels])

    await subscriber.put_history(channels)

    assert subscriber.qsize == expected_entries


@pytest.mark.parametrize("join", [False, True])
async def test_stop(join: bool) -> None:
    subscriber = Subscriber(AsyncMock())
    subscriber.start_in_background(AsyncMock())
    subscriber.put_nowait(b"foo")

    await subscriber.stop(join=join)

    assert subscriber._task is None


@pytest.mark.parametrize("join", [False, True])
async def test_stop_no_task(join: bool) -> None:
    subscriber = Subscriber(AsyncMock())

    await subscriber.stop(join=join)


async def test_context_manager() -> None:
    subscriber = Subscriber(AsyncMock())
    async with subscriber.run_in_background(AsyncMock()):
        assert subscriber._task

    assert not subscriber._task
