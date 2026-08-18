from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack, suppress
from typing import TYPE_CHECKING, Any

from psycopg import AsyncConnection
from psycopg.sql import SQL, Identifier

from litestar.channels.backends.base import ChannelsBackend

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Iterable

_LISTEN_POLL_INTERVAL = 0.1
"""Duration of a single ``notifies()`` pass, after which the listener re-checks whether to stop."""

_STOP_LISTENER_TIMEOUT = 5.0
"""How long to wait for the listener to stop on its own before falling back to cancellation."""


class PsycoPgChannelsBackend(ChannelsBackend):
    _listener_conn: AsyncConnection[Any]
    _listener_lock: asyncio.Lock

    def __init__(self, pg_dsn: str) -> None:
        self._pg_dsn = pg_dsn
        self._subscribed_channels: set[str] = set()
        self._exit_stack = AsyncExitStack()
        self._listener_task: asyncio.Task[None] | None = None
        self._event_queue: asyncio.Queue[tuple[str, bytes] | Exception] = asyncio.Queue()
        self._shutting_down = False
        self._stop_listening = False

    async def on_startup(self) -> None:
        self._exit_stack = AsyncExitStack()
        self._event_queue = asyncio.Queue()
        self._listener_lock = asyncio.Lock()
        self._shutting_down = False
        self._listener_conn = await AsyncConnection[Any].connect(self._pg_dsn, autocommit=True)
        await self._exit_stack.enter_async_context(self._listener_conn)
        self._start_listener()

    async def on_shutdown(self) -> None:
        async with self._listener_lock:
            self._shutting_down = True
            await self._stop_listener()
            self._subscribed_channels.clear()
            await self._exit_stack.aclose()

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        dec_data = data.decode("utf-8")
        async with await AsyncConnection[Any].connect(self._pg_dsn, autocommit=True) as conn:
            for channel in channels:
                await conn.execute(SQL("NOTIFY {channel}, {data}").format(channel=Identifier(channel), data=dec_data))

    async def subscribe(self, channels: Iterable[str]) -> None:
        requested_channels = set(channels)
        async with self._listener_lock:
            channels_to_subscribe = requested_channels - self._subscribed_channels
            if not channels_to_subscribe:
                return
            await self._stop_listener()
            try:
                for channel in channels_to_subscribe:
                    await self._listener_conn.execute(SQL("LISTEN {channel}").format(channel=Identifier(channel)))
                    self._subscribed_channels.add(channel)
            finally:
                if not self._shutting_down:
                    self._start_listener()

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        requested_channels = set(channels)
        async with self._listener_lock:
            channels_to_unsubscribe = requested_channels & self._subscribed_channels
            if not channels_to_unsubscribe:
                return
            await self._stop_listener()
            try:
                for channel in channels_to_unsubscribe:
                    await self._listener_conn.execute(SQL("UNLISTEN {channel}").format(channel=Identifier(channel)))
                    self._subscribed_channels.remove(channel)
            finally:
                if not self._shutting_down:
                    self._start_listener()

    async def stream_events(self) -> AsyncGenerator[tuple[str, bytes], None]:
        while True:
            event = await self._event_queue.get()
            if isinstance(event, Exception):
                raise event
            if event[0] in self._subscribed_channels:
                yield event

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        raise NotImplementedError()

    def _start_listener(self) -> None:
        self._stop_listening = False
        self._listener_task = asyncio.create_task(self._listen())

    async def _stop_listener(self) -> None:
        if self._listener_task is None:
            return
        self._stop_listening = True
        try:
            await asyncio.wait_for(asyncio.shield(self._listener_task), _STOP_LISTENER_TIMEOUT)
        except asyncio.TimeoutError:
            self._listener_task.cancel()
            with suppress(asyncio.CancelledError, asyncio.TimeoutError):
                await asyncio.wait_for(asyncio.shield(self._listener_task), _STOP_LISTENER_TIMEOUT)
        self._listener_task = None

    async def _listen(self) -> None:
        try:
            while not self._stop_listening:
                async for notify in self._listener_conn.notifies(timeout=_LISTEN_POLL_INTERVAL):
                    self._event_queue.put_nowait((notify.channel, notify.payload.encode("utf-8")))
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # noqa: BLE001 - listener failures are forwarded to stream consumers
            self._event_queue.put_nowait(exc)
