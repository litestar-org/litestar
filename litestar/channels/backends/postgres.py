from __future__ import annotations

import asyncio
from typing import AsyncGenerator, Iterable

import asyncpg
import psycopg

from .base import ChannelsBackend


class AsyncPgChannelsBackend(ChannelsBackend):
    def __init__(self, url: str) -> None:
        self._pg_url = url
        self._listener_conn: asyncpg.Connection
        self._queue: asyncio.Queue[tuple[str, bytes]] = asyncio.Queue()
        self._subscribed_channels: set[str] = set()

    async def on_startup(self) -> None:
        self._listener_conn = await asyncpg.connect(self._pg_url)

    async def on_shutdown(self) -> None:
        await self._listener_conn.close()
        del self._listener_conn

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        dec_data = data.decode("utf-8")

        conn = await asyncpg.connect(self._pg_url)
        try:
            for channel in channels:
                await conn.execute("SELECT pg_notify($1, $2);", channel, dec_data)
        finally:
            await conn.close()

    async def subscribe(self, channels: Iterable[str]) -> None:
        for channel in set(channels) - self._subscribed_channels:
            await self._listener_conn.add_listener(channel, self._listener)  # type: ignore[arg-type]
            self._subscribed_channels.add(channel)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        for channel in channels:
            await self._listener_conn.remove_listener(channel, self._listener)  # type: ignore[arg-type]
        self._subscribed_channels = self._subscribed_channels - set(channels)

    async def stream_events(self) -> AsyncGenerator[tuple[str, bytes], None]:
        while self._queue:
            yield await self._queue.get()
            self._queue.task_done()

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        raise NotImplementedError()

    def _listener(self, /, connection: asyncpg.Connection, pid: int, channel: str, payload: object) -> None:
        if not isinstance(payload, str):
            raise RuntimeError("Invalid data received")
        self._queue.put_nowait((channel, payload.encode("utf-8")))


class PsycoPgChannelsBackend(ChannelsBackend):
    def __init__(self, url: str) -> None:
        self._pg_url = url
        self._listener_conn: psycopg.AsyncConnection
        self._subscribed_channels: set[str] = set()

    async def on_startup(self) -> None:
        self._listener_conn = await psycopg.AsyncConnection.connect(self._pg_url, autocommit=True)

    async def on_shutdown(self) -> None:
        await self._listener_conn.close()
        del self._listener_conn

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        dec_data = data.decode("utf-8")
        async with await psycopg.AsyncConnection.connect(self._pg_url) as conn:
            for channel in channels:
                await conn.execute("SELECT pg_notify(%s, %s);", (channel, dec_data))

    async def subscribe(self, channels: Iterable[str]) -> None:
        for channel in set(channels) - self._subscribed_channels:
            await self._listener_conn.execute(f"LISTEN {channel}")
            self._subscribed_channels.add(channel)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        for channel in channels:
            await self._listener_conn.execute(f"UNLISTEN {channel}")
        self._subscribed_channels = self._subscribed_channels - set(channels)

    async def stream_events(self) -> AsyncGenerator[tuple[str, bytes], None]:
        async for notify in self._listener_conn.notifies():
            yield notify.channel, notify.payload.encode("utf-8")

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        raise NotImplementedError()
