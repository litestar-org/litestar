from __future__ import annotations

from contextlib import AsyncExitStack
from typing import Any, AsyncGenerator, Iterable

from psycopg import AsyncConnection
from psycopg.sql import SQL, Identifier

from litestar.channels.backends.base import ChannelsBackend


class PsycoPgChannelsBackend(ChannelsBackend):
    _listener_conn: AsyncConnection[Any]

    def __init__(self, pg_dsn: str) -> None:
        self._pg_dsn = pg_dsn
        self._subscribed_channels: set[str] = set()
        self._exit_stack = AsyncExitStack()

    async def on_startup(self) -> None:
        self._listener_conn = await AsyncConnection[Any].connect(self._pg_dsn, autocommit=True)
        await self._exit_stack.enter_async_context(self._listener_conn)

    async def on_shutdown(self) -> None:
        await self._exit_stack.aclose()

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

    async def stream_events(self) -> AsyncGenerator[tuple[str, bytes], None]:
        async for notify in self._listener_conn.notifies():
            yield notify.channel, notify.payload.encode("utf-8")

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        raise NotImplementedError()
