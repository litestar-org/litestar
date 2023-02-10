from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING

from starlite.types import Empty, EmptyType

if TYPE_CHECKING:
    from typing_extensions import Self


class StorageBackend(ABC):
    @abstractmethod
    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        pass

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        pass

    @abstractmethod
    async def delete(self, key: str) -> None:
        pass


class NamespacedStorageBackend(StorageBackend):
    __slots__ = ("namespace",)

    def __init__(self, namespace: str | None | EmptyType = Empty) -> None:
        self.namespace = "STARLITE" if namespace is Empty else namespace

    def make_key(self, key: str) -> str:
        if self.namespace:
            return f"{self.namespace}_{key}"
        return key

    @abstractmethod
    def with_namespace(self, namespace: str) -> Self:
        pass


class StorageObject:
    """A container class for cache data."""

    def __init__(self, data: bytes, expires: datetime | None = None) -> None:
        self.data = data
        self.expires = expires

    @property
    def expired(self) -> bool:
        return self.expires is not None and datetime.now() >= self.expires
