from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from typing import TYPE_CHECKING, Any

from psycopg import AsyncConnection, OperationalError
from psycopg.sql import SQL, Identifier

from litestar.channels.backends.base import ChannelsBackend

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Iterable


class PsycoPgChannelsBackend(ChannelsBackend):
    # Bounds how long notifies() holds the connection lock, so it also bounds
    # the worst-case latency for subscribe/unsubscribe to acquire it.
    _NOTIFIES_TIMEOUT: float = 0.1

    _listener_conn: AsyncConnection[Any]
    _queue: asyncio.Queue[tuple[str, bytes]]
    _pump_task: asyncio.Task[None]

    def __init__(self, pg_dsn: str) -> None:
        self._pg_dsn = pg_dsn
        self._subscribed_channels: set[str] = set()
        self._exit_stack = AsyncExitStack()

    async def on_startup(self) -> None:
        self._listener_conn = await AsyncConnection[Any].connect(self._pg_dsn, autocommit=True)
        await self._exit_stack.enter_async_context(self._listener_conn)
        self._queue = asyncio.Queue()
        self._pump_task = asyncio.create_task(self._pump_notifications())

    async def on_shutdown(self) -> None:
        # Closing the connection makes the pump's notifies() raise OperationalError,
        # which the pump catches; awaiting then completes once it returns.
        await self._exit_stack.aclose()
        await self._pump_task

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        dec_data = data.decode("utf-8")
        async with await AsyncConnection[Any].connect(self._pg_dsn, autocommit=True) as conn:
            for channel in channels:
                await conn.execute(SQL("NOTIFY {channel}, {data}").format(channel=Identifier(channel), data=dec_data))

    async def subscribe(self, channels: Iterable[str]) -> None:
        for channel in set(channels) - self._subscribed_channels:
            await self._listener_conn.execute(SQL("LISTEN {channel}").format(channel=Identifier(channel)))
            self._subscribed_channels.add(channel)
        await self._listener_conn.commit()

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        for channel in channels:
            await self._listener_conn.execute(SQL("UNLISTEN {channel}").format(channel=Identifier(channel)))
            await self._listener_conn.commit()

        self._subscribed_channels = self._subscribed_channels - set(channels)

    async def _pump_notifications(self) -> None:
        # psycopg 3.2+ holds the connection lock across notifies(); cycling on a
        # short timeout lets subscribe/unsubscribe interleave between iterations.
        try:
            while True:
                async for notify in self._listener_conn.notifies(timeout=self._NOTIFIES_TIMEOUT):
                    self._queue.put_nowait((notify.channel, notify.payload.encode("utf-8")))
        except OperationalError:
            return  # connection closed during shutdown

    async def stream_events(self) -> AsyncGenerator[tuple[str, bytes], None]:
        while True:
            channel, message = await self._queue.get()
            # Drop messages for channels that were unsubscribed in the meantime.
            if channel in self._subscribed_channels:
                yield channel, message

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        raise NotImplementedError()
