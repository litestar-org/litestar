from __future__ import annotations

from datetime import datetime, timedelta

from anyio import Lock

from .base import StorageBackend


class StorageObject:
    """A container class for cache data."""

    def __init__(self, value: bytes, expiration: datetime | None = None) -> None:
        self.value = value
        self.expiration = expiration

    @property
    def expired(self) -> bool:
        return self.expiration is not None and datetime.now() >= self.expiration


class MemoryStorageBackend(StorageBackend):
    __slots__ = ("_store", "_lock")

    def __init__(self, key_prefix: str | None = None) -> None:
        super().__init__(key_prefix=key_prefix)
        self._store: dict[str, StorageObject] = {}
        self._lock = Lock()

    def with_key_prefix(self, key_prefix: str) -> MemoryStorageBackend:
        new = type(self)(key_prefix=key_prefix)
        new._store = self._store
        new._lock = self._lock
        return new

    async def get(self, key: str) -> bytes | None:
        key = self.make_key(key)
        async with self._lock:
            cache_obj = self._store.get(key)

        if cache_obj:
            if not cache_obj.expired:
                return cache_obj.value

            await self.delete(key)

        return None

    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        expiration: datetime | None = None
        if expires:
            expiration = datetime.now() + timedelta(seconds=expires)
        async with self._lock:
            self._store[self.make_key(key)] = StorageObject(value=value, expiration=expiration)

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(self.make_key(key), None)

    async def delete_all(self) -> None:
        async with self._lock:
            if not self.key_prefix:
                self._store.clear()
            else:
                for key in set(self._store.keys()):
                    if key.startswith(self.key_prefix):
                        self._store.pop(key)
