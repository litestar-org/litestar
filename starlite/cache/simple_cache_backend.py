from asyncio import Lock
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict

from starlite.cache.base import CacheBackendProtocol


@dataclass()
class CacheObject:
    """A container class for cache data."""

    value: Any
    """ cache data """
    expiration: datetime
    """ timestamp of cache """


class SimpleCacheBackend(CacheBackendProtocol):
    def __init__(self) -> None:
        """This class offers a simple thread safe cache backend that stores
        values in local memory using a `dict`."""
        self._store: Dict[str, CacheObject] = {}
        self._lock = Lock()

    async def get(self, key: str) -> Any:  # pylint: disable=invalid-overridden-method
        """Retrieve value from cache corresponding to the given key.

        Args:
            key: name of cached value.

        Returns:
            Cached value or `None`.
        """
        async with self._lock:
            cache_obj = self._store.get(key)

        if cache_obj:
            if cache_obj.expiration >= datetime.now():
                return cache_obj.value
            await self.delete(key)

        return None

    async def set(self, key: str, value: Any, expiration: int) -> None:  # pylint: disable=invalid-overridden-method
        """Set a value in cache for a given key with a given expiration in
        seconds.

        Args:
            key: key to cache `value` under.
            value: the value to be cached.
            expiration: expiration of cached value in seconds.

        Returns:
            None
        """
        async with self._lock:
            self._store[key] = CacheObject(value=value, expiration=datetime.now() + timedelta(seconds=expiration))
        return None

    async def delete(self, key: str) -> None:  # pylint: disable=invalid-overridden-method
        """Remove a value from the cache for a given key.

        Args:
            key: key to be deleted from the cache.

        Returns:
            None
        """
        async with self._lock:
            self._store.pop(key, None)
        return None
