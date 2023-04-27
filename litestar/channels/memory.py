from __future__ import annotations

import asyncio
from asyncio import Queue
from collections import defaultdict, deque
from typing import Any, AsyncGenerator, Iterable

from litestar.channels.base import ChannelsBackend


class MemoryChannelsBackend(ChannelsBackend):
    def __init__(self, history: int = 0) -> None:
        self._max_history_length = history
        self._channels: set[str] = set()
        self._queue: Queue[tuple[str, bytes]] | None = None
        self._history: defaultdict[str, deque[bytes]] = defaultdict(lambda: deque(maxlen=self._max_history_length))

    async def on_startup(self) -> None:
        self._queue = Queue()

    async def on_shutdown(self) -> None:
        self._queue = None

    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        if not self._queue:
            raise RuntimeError()
        for channel in channels:
            await self._queue.put((channel, data))
        if self._max_history_length:
            for channel in channels:
                self._history[channel].append(data)

    async def subscribe(self, channels: Iterable[str]) -> None:
        self._channels.update(channels)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        self._channels = self._channels - (set(channels))
        for channel in channels:
            del self._history[channel]

    async def stream_events(self) -> AsyncGenerator[tuple[str, Any], None]:
        while self._queue:
            if not len(self._channels):
                await asyncio.sleep(0)
                continue
            yield await self._queue.get()
            self._queue.task_done()

    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        history = list(self._history[channel])
        if limit:
            history = history[-limit:]
        return history
