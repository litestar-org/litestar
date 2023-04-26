from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, AsyncGenerator, Iterable

if TYPE_CHECKING:
    from litestar.types import LitestarEncodableType


class ChannelsBackend(ABC):
    @abstractmethod
    async def on_startup(self) -> None:
        ...

    @abstractmethod
    async def on_shutdown(self) -> None:
        ...

    @abstractmethod
    async def publish(self, data: LitestarEncodableType, channels: Iterable[str]) -> None:
        ...

    @abstractmethod
    async def subscribe(self, channels: Iterable[str]) -> None:
        ...

    @abstractmethod
    async def unsubscribe(self, channels: Iterable[str]) -> None:
        ...

    @abstractmethod
    def stream_events(self) -> AsyncGenerator[tuple[Any, set[str]], None]:
        ...
