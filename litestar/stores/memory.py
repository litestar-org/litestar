from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING

import anyio
from anyio import Lock

from .base import StorageObject, Store

__all__ = ("MemoryStore",)


if TYPE_CHECKING:
    from datetime import timedelta


def _size_of(key: str, data: bytes) -> int:
    return len(key) * (1 if key.isascii() else 4) + len(data)


class MemoryStore(Store):
    """In memory, atomic, asynchronous key/value store."""

    __slots__ = ("_lock", "_max_entries", "_max_size", "_size", "_store")

    def __init__(self, *, max_size: int | None = None, max_entries: int | None = None) -> None:
        """Initialize :class:`MemoryStore`

        Args:
            max_size: Maximum total size in bytes of the stored keys and values. If
                storing a value exceeds it, the oldest values are deleted until it
                fits. A value that, together with its key, is larger than ``max_size``
                is not stored, and any value stored under its key is deleted
            max_entries: Maximum number of stored values. If storing a value exceeds
                it, the oldest values are deleted
        """
        self._store: dict[str, StorageObject] = {} if max_size is None and max_entries is None else OrderedDict()
        self._lock = Lock()
        self._max_size = max_size
        self._max_entries = max_entries
        self._size = 0

    def _pop(self, key: str) -> None:
        storage_obj = self._store.pop(key, None)
        if storage_obj and self._max_size is not None:
            self._size -= _size_of(key, storage_obj.data)

    def _is_full(self) -> bool:
        return (self._max_size is not None and self._size > self._max_size) or (
            self._max_entries is not None and len(self._store) > self._max_entries
        )

    async def set(self, key: str, value: str | bytes, expires_in: int | timedelta | None = None) -> None:
        """Set a value.

        If ``max_size`` or ``max_entries`` is exceeded, the oldest values are deleted.

        Args:
            key: Key to associate the value with
            value: Value to store
            expires_in: Time in seconds before the key is considered expired

        Returns:
            ``None``
        """
        if isinstance(value, str):
            value = value.encode("utf-8")
        async with self._lock:
            if self._max_size is None and self._max_entries is None:
                self._store[key] = StorageObject.new(data=value, expires_in=expires_in)
                return

            self._pop(key)
            if self._max_size is not None:
                size = _size_of(key, value)
                if size > self._max_size:
                    return
                self._size += size

            self._store[key] = StorageObject.new(data=value, expires_in=expires_in)
            while self._store and self._is_full():
                self._pop(next(iter(self._store)))

    async def get(self, key: str, renew_for: int | timedelta | None = None) -> bytes | None:
        """Get a value.

        Args:
            key: Key associated with the value
            renew_for: If given and the value had an initial expiry time set, renew the
                expiry time for ``renew_for`` seconds. If the value has not been set
                with an expiry time this is a no-op

        Returns:
            The value associated with ``key`` if it exists and is not expired, else
            ``None``
        """
        async with self._lock:
            storage_obj = self._store.get(key)

            if not storage_obj:
                return None

            if storage_obj.expired:
                self._pop(key)
                return None

            if renew_for and storage_obj.expires_at:
                # don't use .set() here, so we can hold onto the lock for the whole operation
                storage_obj = StorageObject.new(data=storage_obj.data, expires_in=renew_for)
                self._store[key] = storage_obj

            return storage_obj.data

    async def delete(self, key: str) -> None:
        """Delete a value.

        If no such key exists, this is a no-op.

        Args:
            key: Key of the value to delete
        """
        async with self._lock:
            self._pop(key)

    async def delete_all(self) -> None:
        """Delete all stored values."""
        async with self._lock:
            self._store.clear()
            self._size = 0

    async def delete_expired(self) -> None:
        """Delete expired items.

        Since expired items are normally only cleared on access (i.e. when calling
        :meth:`.get`), this method should be called in regular intervals
        to free memory.
        """
        async with self._lock:
            new_store = type(self._store)()
            for i, (key, storage_obj) in enumerate(self._store.items()):
                if not storage_obj.expired:
                    new_store[key] = storage_obj
                if i % 1000 == 0:
                    await anyio.sleep(0)
            self._store = new_store
            if self._max_size is not None:
                self._size = sum(_size_of(key, storage_obj.data) for key, storage_obj in new_store.items())

    async def exists(self, key: str) -> bool:
        """Check if a given ``key`` exists."""
        return key in self._store

    async def expires_in(self, key: str) -> int | None:
        """Get the time in seconds ``key`` expires in. If no such ``key`` exists or no
        expiry time was set, return ``None``.
        """
        if storage_obj := self._store.get(key):
            return storage_obj.expires_in
        return None
