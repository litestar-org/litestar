from __future__ import annotations

from abc import ABC, abstractmethod
from typing import AsyncGenerator, Iterable


class ChannelsBackend(ABC):
    @abstractmethod
    async def on_startup(self) -> None:
        ...

    @abstractmethod
    async def on_shutdown(self) -> None:
        ...

    @abstractmethod
    async def publish(self, data: bytes, channels: Iterable[str]) -> None:
        ...

    @abstractmethod
    async def subscribe(self, channels: Iterable[str]) -> None:
        ...

    @abstractmethod
    async def unsubscribe(self, channels: Iterable[str]) -> None:
        ...

    @abstractmethod
    def stream_events(self) -> AsyncGenerator[tuple[str, bytes], None]:
        ...

    @abstractmethod
    async def get_history(self, channel: str, limit: int | None = None) -> list[bytes]:
        ...
