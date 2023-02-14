from __future__ import annotations

from typing import TYPE_CHECKING

from anyio import Lock

from .base import StorageBackend, StorageObject

if TYPE_CHECKING:
    from datetime import timedelta


class MemoryStorageBackend(StorageBackend):
    __slots__ = ("_store", "_lock")

    def __init__(self) -> None:
        self._store: dict[str, StorageObject] = {}
        self._lock = Lock()

    async def set(self, key: str, value: bytes, expires_in: int | timedelta | None = None) -> None:
        async with self._lock:
            self._store[key] = StorageObject.new(data=value, expires_in=expires_in)

    async def get(self, key: str, renew_for: int | timedelta | None = None) -> bytes | None:
        async with self._lock:
            storage_obj = self._store.get(key)

            if not storage_obj:
                return None

            if storage_obj.expired:
                self._store.pop(key)
                return None

            if renew_for and storage_obj.expires_at:
                # don't use .set() here, so we can hold onto the lock for the whole operation
                storage_obj = StorageObject.new(data=storage_obj.data, expires_in=renew_for)
                self._store[key] = storage_obj

            return storage_obj.data

    async def delete(self, key: str) -> None:
        async with self._lock:
            self._store.pop(key, None)

    async def delete_all(self) -> None:
        async with self._lock:
            self._store.clear()

    async def exists(self, key: str) -> bool:
        return key in self._store

    async def expires_in(self, key: str) -> int | None:
        if storage_obj := self._store.get(key):
            return storage_obj.expires_in
        return None
