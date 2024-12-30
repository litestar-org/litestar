from __future__ import annotations

import logging
from contextlib import AsyncExitStack
from typing import AsyncGenerator, Iterable

import psycopg
from psycopg.sql import SQL, Identifier

from .base import ChannelsBackend

logger = logging.getLogger(__name__)


def _safe_quote(ident: str) -> str:
    return '"{}"'.format(ident.replace('"', '""'))  # sourcery skip


class PsycoPgChannelsBackend(ChannelsBackend):
    _listener_conn: psycopg.AsyncConnection

    def __init__(self, pg_dsn: str) -> None:
        self._pg_dsn = pg_dsn
        self._subscribed_channels: set[str] = set()
        self._exit_stack = AsyncExitStack()

    async def on_startup(self) -> None:
        logger.debug("Starting up PsycoPgChannelsBackend")
        self._listener_conn = await psycopg.AsyncConnection.connect(self._pg_dsn, autocommit=True)
        await self._exit_stack.enter_async_context(self._listener_conn)
        logger.debug("PsycoPgChannelsBackend startup complete")

    async def on_shutdown(self) -> None:
        logger.debug("Shutting down PsycoPgChannelsBackend")
        await self._exit_stack.aclose()
        logger.debug("PsycoPgChannelsBackend shutdown complete")

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        dec_data = data.decode("utf-8")
        logger.debug("Publishing data to channels: %s with data: %s", channels, dec_data)
        async with await psycopg.AsyncConnection.connect(self._pg_dsn, autocommit=True) as conn:
            for channel in channels:
                await conn.execute("SELECT pg_notify(%s, %s);", (channel, dec_data))
                logger.debug("Published to channel: %s", channel)

    async def subscribe(self, channels: Iterable[str]) -> None:
        channels_to_subscribe = set(channels) - self._subscribed_channels
        if not channels_to_subscribe:
            logger.debug("No new channels to subscribe: %s", channels)
            return

        for channel in channels_to_subscribe:
            await self._listener_conn.execute(SQL("LISTEN {}").format(Identifier(channel)))
            logger.debug("Subscribed to channel: %s", channel)
            self._subscribed_channels.add(channel)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        for channel in channels:
            await self._listener_conn.execute(SQL("UNLISTEN {}").format(Identifier(channel)))
            logger.debug("Unsubscribed from channel: %s", channel)
        self._subscribed_channels -= set(channels)
        logger.debug("Current subscribed channels: %s", self._subscribed_channels)

    async def stream_events(self) -> AsyncGenerator[tuple[str, bytes], None]:
        logger.debug("Starting to stream events")
        async for notify in self._listener_conn.notifies():
            logger.debug("Received notify: %s - %s", notify.channel, notify.payload)
            yield notify.channel, notify.payload.encode("utf-8")

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        raise NotImplementedError()
