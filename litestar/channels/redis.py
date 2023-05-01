from __future__ import annotations

import asyncio
import importlib.resources
from abc import ABC
from datetime import datetime, timedelta, timezone
from functools import partial
from typing import TYPE_CHECKING, Any, AsyncGenerator, Iterable, cast

import anyio

from litestar.exceptions import ImproperlyConfiguredException

from .base import ChannelsBackend

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from redis.asyncio.client import PubSub


class RedisChannelsBackend(ChannelsBackend, ABC):
    def __init__(self, *, stream_sleep_no_subscriptions: int, redis: Redis) -> None:
        self._redis = redis
        self._key_prefix = "LITESTAR_CHANNELS"
        self._stream_sleep_no_subscriptions = stream_sleep_no_subscriptions / 1000

    def _make_key(self, channel: str) -> str:
        return f"{self._key_prefix}_{channel.upper()}"


class RedisChannelsPubSubBackend(RedisChannelsBackend):
    def __init__(self, *, redis: Redis, stream_sleep_no_subscriptions: int = 1) -> None:
        super().__init__(redis=redis, stream_sleep_no_subscriptions=stream_sleep_no_subscriptions)
        self._pub_sub: PubSub = self._redis.pubsub()

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        await self._pub_sub.reset()

    async def subscribe(self, channels: Iterable[str]) -> None:
        await self._pub_sub.subscribe(*channels)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        await self._pub_sub.unsubscribe(*channels)

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        channels = set(channels)
        if len(channels) == 1:
            await self._redis.publish(channels.pop(), data)
            return

        async with anyio.create_task_group() as task_group:
            for channel in channels:
                task_group.start_soon(self._redis.publish, channel, data)

    async def stream_events(self) -> AsyncGenerator[tuple[str, Any], None]:
        if not self._pub_sub:
            raise RuntimeError()

        while True:
            if not self._pub_sub.subscribed:
                await asyncio.sleep(self._stream_sleep_no_subscriptions)  # no subscriptions found so we sleep a bit
                continue
            message = await self._pub_sub.get_message(ignore_subscribe_messages=True, timeout=None)  # type: ignore[arg-type]
            if message is None:
                continue
            channel = message["channel"].decode()
            data = message["data"]
            yield channel, data

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        raise NotImplementedError()


class RedisChannelsStreamBackend(RedisChannelsBackend):
    def __init__(
        self,
        history: int = 0,
        *,
        redis: Redis,
        cap_streams_approximate: bool = True,
        stream_sleep_no_subscriptions: int = 1,
    ) -> None:
        super().__init__(redis=redis, stream_sleep_no_subscriptions=stream_sleep_no_subscriptions)
        if history < 1:
            raise ImproperlyConfiguredException("history must be greater than 0")

        self._history_limit = history
        self._subscribed_channels: set[str] = set()
        self._cap_streams_approximate = cap_streams_approximate
        self._prune_streams_script = self._redis.register_script(
            importlib.resources.read_text("litestar.channels", "_redis_prune_streams.lua")
        )
        self._flush_all_streams_script = self._redis.register_script(
            importlib.resources.read_text("litestar.channels", "_redis_flushall.lua")
        )

    async def on_startup(self) -> None:
        pass

    async def on_shutdown(self) -> None:
        pass

    async def subscribe(self, channels: Iterable[str]) -> None:
        self._subscribed_channels.update(channels)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        self._subscribed_channels = self._subscribed_channels - set(channels)

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        channels = set(channels)
        if len(channels) == 1:
            channel = channels.pop()
            await self._redis.xadd(
                name=self._make_key(channel),
                fields={"data": data, "channel": channel},
                maxlen=self._history_limit,
                approximate=self._cap_streams_approximate,
            )
            return

        async with anyio.create_task_group() as task_group:
            for channel in channels:
                task_group.start_soon(
                    partial(
                        self._redis.xadd,
                        name=self._make_key(channel),
                        fields={"data": data, "channel": channel},
                        maxlen=self._history_limit,
                        approximate=self._cap_streams_approximate,
                    )
                )

    async def stream_events(self) -> AsyncGenerator[tuple[str, Any], None]:
        stream_ids: dict[str, bytes] = {}
        while True:
            stream_keys = [self._make_key(c) for c in self._subscribed_channels]
            if not stream_keys:
                await asyncio.sleep(self._stream_sleep_no_subscriptions)  # no subscriptions found so we sleep a bit
                continue
            data: list[tuple[bytes, list[tuple[bytes, dict[bytes, bytes]]]]] = await self._redis.xread(
                {key: stream_ids.get(key, 0) for key in stream_keys}, block=1
            )
            if not data:
                continue
            for stream_key, channel_events in data:
                for event in channel_events:
                    event_data = event[1][b"data"]
                    channel_name = event[1][b"channel"].decode()
                    stream_ids[stream_key.decode()] = event[0]
                    yield channel_name, event_data

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        data: Iterable[tuple[bytes, dict[bytes, bytes]]]
        if limit:
            data = reversed(await self._redis.xrevrange(self._make_key(channel), count=limit))
        else:
            data = await self._redis.xrange(self._make_key(channel))

        return [event[b"data"] for _, event in data]

    async def prune_streams(self, cutoff: timedelta) -> int:
        timestamp = str(int((datetime.now(tz=timezone.utc) - cutoff).timestamp() * 1000))
        deleted_streams = await self._prune_streams_script(keys=[], args=[f"{self._key_prefix}*", timestamp])
        return cast("int", deleted_streams)

    async def flush_all(self) -> int:
        deleted_streams = await self._flush_all_streams_script(keys=[], args=[f"{self._key_prefix}*"])
        return cast("int", deleted_streams)
