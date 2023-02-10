from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typing_extensions import Self


class StorageBackend(ABC):
    __slots__ = ("default_expiration", "key_prefix")

    def __init__(self, key_prefix: str | None = None) -> None:
        self.key_prefix = key_prefix

    def make_key(self, key: str) -> str:
        return self.key_prefix or "" + key

    @abstractmethod
    def with_key_prefix(self, key_prefix: str) -> Self:
        pass

    @abstractmethod
    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        pass

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass
