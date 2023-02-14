from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Optional

from msgspec import Struct
from msgspec.msgpack import decode as msgpack_decode
from msgspec.msgpack import encode as msgpack_encode


class StorageBackend(ABC):  # pragma: no cover
    @abstractmethod
    async def set(self, key: str, value: bytes, expires_in: int | timedelta | None = None) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str, renew_for: int | timedelta | None = None) -> bytes | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_all(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def expires_in(self, key: str) -> int | None:
        raise NotImplementedError


class StorageObject(Struct):
    expires_at: Optional[datetime]
    data: bytes

    @classmethod
    def new(cls, data: bytes, expires_in: int | timedelta | None) -> StorageObject:
        if expires_in is not None and not isinstance(expires_in, timedelta):
            expires_in = timedelta(seconds=expires_in)
        return cls(
            data=data,
            expires_at=(datetime.now() + expires_in) if expires_in else None,
        )

    @property
    def expired(self) -> bool:
        return self.expires_at is not None and datetime.now() >= self.expires_at

    @property
    def expires_in(self) -> int:
        if self.expires_at:
            return (self.expires_at - datetime.now()).seconds
        return -1

    def to_bytes(self) -> bytes:
        return msgpack_encode(self)

    @classmethod
    def from_bytes(cls, raw: bytes) -> StorageObject:
        return msgpack_decode(raw, type=cls)
