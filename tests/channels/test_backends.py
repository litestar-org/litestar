from __future__ import annotations

import asyncio
from datetime import timedelta
from typing import AsyncGenerator, cast

import pytest
from _pytest.fixtures import FixtureRequest

from litestar.channels import ChannelsBackend
from litestar.channels.redis import RedisChannelsPubSubBackend, RedisChannelsStreamBackend
from litestar.utils.compat import async_next

pytestmark = [pytest.mark.usefixtures("redis_service")]


@pytest.fixture(
    params=[
        pytest.param("redis_pub_sub_backend", id="redis:pubsub"),
        pytest.param("redis_stream_backend", id="redis:stream"),
        pytest.param("memory_backend", id="memory"),
    ]
)
def channels_backend_instance(request: FixtureRequest) -> ChannelsBackend:
    return cast(ChannelsBackend, request.getfixturevalue(request.param))


@pytest.fixture()
async def channels_backend(channels_backend_instance: ChannelsBackend) -> AsyncGenerator[ChannelsBackend, None]:
    await channels_backend_instance.on_startup()
    yield channels_backend_instance
    await channels_backend_instance.on_shutdown()


@pytest.mark.parametrize("channels", [{"foo"}, {"foo", "bar"}])
async def test_pub_sub(channels_backend: ChannelsBackend, channels: set[str]) -> None:
    await channels_backend.subscribe(channels)
    await channels_backend.publish(b"something", channels)

    event_generator = channels_backend.stream_events()
    received = set()
    for _ in channels:
        received.add(await async_next(event_generator))
    assert received == {(c, b"something") for c in channels}


async def test_pub_sub_no_subscriptions(channels_backend: ChannelsBackend) -> None:
    await channels_backend.publish(b"something", ["foo"])

    event_generator = channels_backend.stream_events()
    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        await asyncio.wait_for(async_next(event_generator), timeout=0.01)


async def test_pub_sub_no_subscriptions_by_unsubscribes(channels_backend: ChannelsBackend) -> None:
    await channels_backend.subscribe(["foo"])
    await channels_backend.publish(b"something", ["foo"])

    event_generator = channels_backend.stream_events()
    await asyncio.wait_for(async_next(event_generator), timeout=0.01)
    await channels_backend.unsubscribe(["foo"])
    await channels_backend.publish(b"something", ["foo"])

    with pytest.raises((asyncio.TimeoutError, TimeoutError)):
        await asyncio.wait_for(async_next(event_generator), timeout=0.01)


async def test_pub_sub_shutdown_leftover_messages(channels_backend_instance: ChannelsBackend) -> None:
    await channels_backend_instance.on_startup()

    await channels_backend_instance.publish(b"something", {"foo"})

    await asyncio.wait_for(channels_backend_instance.on_shutdown(), timeout=0.1)


@pytest.mark.parametrize("history_limit,expected_history_length", [(None, 10), (1, 1), (5, 5), (10, 10)])
async def test_get_history(
    channels_backend: ChannelsBackend, history_limit: int | None, expected_history_length: int
) -> None:
    if isinstance(channels_backend, RedisChannelsPubSubBackend):
        pytest.skip()
    messages = [str(i).encode() for i in range(100)]
    for message in messages:
        await channels_backend.publish(message, {"something"})

    history = await channels_backend.get_history("something", history_limit)

    expected_messages = messages[-expected_history_length:]
    assert len(history) == expected_history_length
    assert history == expected_messages


async def test_memory_backend_discards_history_entries(channels_backend: ChannelsBackend) -> None:
    if isinstance(channels_backend, RedisChannelsPubSubBackend):
        pytest.skip()

    for _ in range(20):
        await channels_backend.publish(b"foo", {"bar"})

    assert len(await channels_backend.get_history("bar")) == 10


async def test_redis_stream_backend_prune_streams(redis_stream_backend: RedisChannelsStreamBackend) -> None:
    await redis_stream_backend.publish(b"something", ["foo"])
    await asyncio.sleep(2 / 1000)
    await redis_stream_backend.publish(b"something", ["bar"])

    deleted_streams_count = await redis_stream_backend.prune_streams(timedelta(milliseconds=1))

    assert deleted_streams_count == 1
    assert not await redis_stream_backend._redis.xrange(redis_stream_backend._make_key("foo"))
    assert await redis_stream_backend._redis.xrange(redis_stream_backend._make_key("bar"))


async def test_redis_stream_backend_prune_streams_no_hits(redis_stream_backend: RedisChannelsStreamBackend) -> None:
    await redis_stream_backend.publish(b"something", ["foo"])
    await asyncio.sleep(1 / 1000)
    await redis_stream_backend.publish(b"something else", ["foo"])

    deleted_streams_count = await redis_stream_backend.prune_streams(timedelta(milliseconds=1))

    assert deleted_streams_count == 0
    assert await redis_stream_backend._redis.xrange(redis_stream_backend._make_key("foo"))


async def test_redis_streams_backend_flush_all(redis_stream_backend: RedisChannelsStreamBackend) -> None:
    await redis_stream_backend.publish(b"something", ["foo", "bar", "baz"])

    result = await redis_stream_backend.flush_all()

    assert result == 3
