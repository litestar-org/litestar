from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from msgspec import Struct
from msgspec.msgpack import decode as msgpack_decode
from msgspec.msgpack import encode as msgpack_encode

from starlite.types import Empty, EmptyType

if TYPE_CHECKING:
    from typing_extensions import Self


class StorageBackend(ABC):  # pragma: no cover
    @abstractmethod
    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str) -> bytes | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError


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


class StorageObject(Struct):
    expires: Optional[datetime]
    data: bytes

    @property
    def expired(self) -> bool:
        return self.expires is not None and datetime.now() >= self.expires

    def to_bytes(self) -> bytes:
        return msgpack_encode(self)

    @classmethod
    def from_bytes(cls, raw: bytes) -> StorageObject:
        return msgpack_decode(raw, type=cls)
