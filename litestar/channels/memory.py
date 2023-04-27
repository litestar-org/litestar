from __future__ import annotations

from asyncio import Queue
from collections import defaultdict, deque
from typing import TYPE_CHECKING, Any, AsyncGenerator, Iterable

from litestar.channels.base import ChannelsBackend

if TYPE_CHECKING:
    from litestar.types import LitestarEncodableType


class MemoryChannelsBackend(ChannelsBackend):
    def __init__(self, history: int = 0) -> None:
        self._max_history_length = history
        self._channels: set[str] = set()
        self._queue: Queue[tuple[Any, set[str]]] | None = None
        self._history: defaultdict[str, deque] = defaultdict(lambda: deque(maxlen=self._max_history_length))

    async def on_startup(self) -> None:
        self._queue = Queue()

    async def on_shutdown(self) -> None:
        self._queue = None

    async def publish(self, data: LitestarEncodableType, channels: Iterable[str]) -> None:
        if not self._queue:
            raise RuntimeError()
        await self._queue.put((data, set(channels)))
        if self._max_history_length:
            for channel in channels:
                self._history[channel].append(data)

    async def subscribe(self, channels: Iterable[str]) -> None:
        self._channels.update(channels)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        self._channels = self._channels - (set(channels))
        for channel in channels:
            del self._history[channel]

    async def stream_events(self) -> AsyncGenerator[tuple[Any, set[str]], None]:
        while self._queue:
            yield await self._queue.get()
            self._queue.task_done()

    async def get_history(self, channel: str, limit: int | None = None) -> list[str]:
        history = list(self._history[channel])
        if limit:
            history = history[-limit:]
        return history
