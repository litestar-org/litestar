from __future__ import annotations

from asyncio import Queue
from typing import TYPE_CHECKING, Any, AsyncGenerator, Iterable

from litestar.channels.base import ChannelsBackend

if TYPE_CHECKING:
    from litestar.types import LitestarEncodableType


class MemoryChannelsBackend(ChannelsBackend):
    def __init__(self) -> None:
        self._channels: set[str] = set()
        self._queue: Queue[tuple[Any, set[str]]] | None = None

    async def on_startup(self) -> None:
        self._queue = Queue()

    async def on_shutdown(self) -> None:
        if self._queue and not self._queue.empty():
            await self._queue.join()
        self._queue = None

    async def publish(self, data: LitestarEncodableType, channels: Iterable[str]) -> None:
        if not self._queue:
            raise RuntimeError()
        await self._queue.put((data, set(channels)))

    async def subscribe(self, channels: Iterable[str]) -> None:
        self._channels.update(channels)

    async def unsubscribe(self, channels: Iterable[str]) -> None:
        self._channels = self._channels - (set(channels))

    async def received_events(self) -> AsyncGenerator[tuple[Any, set[str]], None]:
        while self._queue:
            yield await self._queue.get()
            self._queue.task_done()
