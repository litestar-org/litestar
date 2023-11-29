import asyncio
from typing import AsyncGenerator, Iterable

import asyncpg

from .base import ChannelsBackend


class PostgresChannelsBackend(ChannelsBackend):
    def __init__(self, url: str) -> None:
        self._pg_url = url
        self._connection: asyncpg.Connection
        self._queue: asyncio.Queue[tuple[str, bytes]] = asyncio.Queue()

    async def on_startup(self) -> None:
        self._connection = await asyncpg.connect(self._pg_url)

    async def on_shutdown(self) -> None:
        await self._connection.close()
        self._connection = None

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        dec_data = data.decode("utf-8")

        for channel in channels:
            await self._connection.execute("SELECT pg_notify($1, $2);", channel, dec_data)

    async def subscribe(self, channels: Iterable[str]) -> None:
        for channel in channels:
            await self._connection.add_listener(channel, self._listener)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        for channel in channels:
            await self._connection.remove_listener(channel, self._listener)

    async def stream_events(self) -> AsyncGenerator[tuple[str, bytes], None]:
        while self._queue:
            yield await self._queue.get()
            self._queue.task_done()

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        pass

    def _listener(
        self, connection: asyncpg.Connection, pid: int, channel: str, payload: object
    ) -> None:
        if not isinstance(payload, str):
            raise RuntimeError()
        self._queue.put_nowait((channel, payload.encode("utf-8")))
