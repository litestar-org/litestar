from __future__ import annotations

import asyncio
import sys

if sys.version_info < (3, 9):
    import importlib_resources  # pragma: no cover
else:
    import importlib.resources as importlib_resources
from abc import ABC
from datetime import timedelta
from typing import TYPE_CHECKING, Any, AsyncGenerator, Iterable, cast

from litestar.channels.backends.base import ChannelsBackend

if TYPE_CHECKING:
    from redis.asyncio import Redis
    from redis.asyncio.client import PubSub

_resource_path = importlib_resources.files("litestar.channels.backends")
_PUBSUB_PUBLISH_SCRIPT = (_resource_path / "_redis_pubsub_publish.lua").read_text()
_FLUSHALL_STREAMS_SCRIPT = (_resource_path / "_redis_flushall_streams.lua").read_text()
_XADD_EXPIRE_SCRIPT = (_resource_path / "_redis_xadd_expire.lua").read_text()


class RedisChannelsBackend(ChannelsBackend, ABC):
    def __init__(self, *, redis: Redis, key_prefix: str, stream_sleep_no_subscriptions: int) -> None:
        """Base redis channels backend.

        Args:
            redis: A :class:`redis.asyncio.Redis` instance
            key_prefix: Key prefix to use for storing data in redis
            stream_sleep_no_subscriptions: Amount of time in milliseconds to pause the
                :meth:`stream_events` generator, should no subscribers exist
        """
        self._redis = redis
        self._key_prefix = key_prefix
        self._stream_sleep_no_subscriptions = stream_sleep_no_subscriptions / 1000

    def _make_key(self, channel: str) -> str:
        return f"{self._key_prefix}_{channel.upper()}"


class RedisChannelsPubSubBackend(RedisChannelsBackend):
    def __init__(
        self, *, redis: Redis, stream_sleep_no_subscriptions: int = 1, key_prefix: str = "LITESTAR_CHANNELS"
    ) -> None:
        """Redis channels backend, `Pub/Sub <https://redis.io/docs/manual/pubsub/>`_.

        This backend provides low overhead and resource usage but no support for history.

        Args:
            redis: A :class:`redis.asyncio.Redis` instance
            key_prefix: Key prefix to use for storing data in redis
            stream_sleep_no_subscriptions: Amount of time in milliseconds to pause the
                :meth:`stream_events` generator, should no subscribers exist
        """
        super().__init__(
            redis=redis, stream_sleep_no_subscriptions=stream_sleep_no_subscriptions, key_prefix=key_prefix
        )
        self.__pub_sub: PubSub | None = None
        self._publish_script = self._redis.register_script(_PUBSUB_PUBLISH_SCRIPT)

    @property
    def _pub_sub(self) -> PubSub:
        if self.__pub_sub is None:
            self.__pub_sub = self._redis.pubsub()
        return self.__pub_sub

    async def on_startup(self) -> None:
        # this method should not do anything in this case
        pass

    async def on_shutdown(self) -> None:
        await self._pub_sub.reset()

    async def subscribe(self, channels: Iterable[str]) -> None:
        """Subscribe to ``channels``, and enable publishing to them"""
        await self._pub_sub.subscribe(*channels)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        """Stop listening for events on ``channels``"""
        await self._pub_sub.unsubscribe(*channels)

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        """Publish ``data`` to ``channels``

        .. note::
            This operation is performed atomically, using a lua script
        """
        await self._publish_script(keys=list(set(channels)), args=[data])

    async def stream_events(self) -> AsyncGenerator[tuple[str, Any], None]:
        """Return a generator, iterating over events of subscribed channels as they become available.

        If no channels have been subscribed to yet via :meth:`subscribe`, sleep for ``stream_sleep_no_subscriptions``
        milliseconds.
        """

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
        """Not implemented"""
        raise NotImplementedError()


class RedisChannelsStreamBackend(RedisChannelsBackend):
    def __init__(
        self,
        history: int,
        *,
        redis: Redis,
        stream_sleep_no_subscriptions: int = 1,
        cap_streams_approximate: bool = True,
        stream_ttl: int | timedelta = timedelta(seconds=60),
        key_prefix: str = "LITESTAR_CHANNELS",
    ) -> None:
        """Redis channels backend, `streams <https://redis.io/docs/data-types/streams/>`_.

        Args:
            history: Amount of messages to keep. This will set a ``MAXLEN`` to the streams
            redis: A :class:`redis.asyncio.Redis` instance
            key_prefix: Key prefix to use for streams
            stream_sleep_no_subscriptions: Amount of time in milliseconds to pause the
                :meth:`stream_events` generator, should no subscribers exist
            cap_streams_approximate: Set the streams ``MAXLEN`` using the ``~`` approximation
                operator for improved performance
            stream_ttl: TTL of a stream in milliseconds or as a timedelta. A streams TTL will be set on each publishing
                operation using ``PEXPIRE``
        """
        super().__init__(
            redis=redis, stream_sleep_no_subscriptions=stream_sleep_no_subscriptions, key_prefix=key_prefix
        )

        self._history_limit = history
        self._subscribed_channels: set[str] = set()
        self._cap_streams_approximate = cap_streams_approximate
        self._stream_ttl = stream_ttl if isinstance(stream_ttl, int) else int(stream_ttl.total_seconds() * 1000)
        self._flush_all_streams_script = self._redis.register_script(_FLUSHALL_STREAMS_SCRIPT)
        self._publish_script = self._redis.register_script(_XADD_EXPIRE_SCRIPT)

    async def on_startup(self) -> None:
        """Called on application startup"""

    async def on_shutdown(self) -> None:
        """Called on application shutdown"""

    async def subscribe(self, channels: Iterable[str]) -> None:
        """Subscribe to ``channels``"""
        self._subscribed_channels.update(channels)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        """Unsubscribe from ``channels``"""
        self._subscribed_channels -= set(channels)

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        """Publish ``data`` to ``channels``.

        .. note::
            This operation is performed atomically, using a Lua script
        """
        channels = set(channels)
        await self._publish_script(
            keys=[self._make_key(key) for key in channels],
            args=[
                data,
                self._history_limit,
                self._stream_ttl,
                int(self._cap_streams_approximate),
                *channels,
            ],
        )

    async def stream_events(self) -> AsyncGenerator[tuple[str, Any], None]:
        """Return a generator, iterating over events of subscribed channels as they become available.

        If no channels have been subscribed to yet via :meth:`subscribe`, sleep for ``stream_sleep_no_subscriptions``
        milliseconds.
        """
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
        """Return the history of ``channels``, returning at most ``limit`` messages"""
        data: Iterable[tuple[bytes, dict[bytes, bytes]]]
        if limit:
            data = reversed(await self._redis.xrevrange(self._make_key(channel), count=limit))
        else:
            data = await self._redis.xrange(self._make_key(channel))

        return [event[b"data"] for _, event in data]

    async def flush_all(self) -> int:
        """Delete all stream keys with the ``key_prefix``.

        .. important::
            This method is incompatible with redis clusters
        """
        deleted_streams = await self._flush_all_streams_script(keys=[], args=[f"{self._key_prefix}*"])
        return cast("int", deleted_streams)
