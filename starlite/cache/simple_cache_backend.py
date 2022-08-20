from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Any, Dict, cast

from starlite.cache.base import CacheBackendProtocol

if TYPE_CHECKING:
    from typing import Optional


class SimpleCacheBackend(CacheBackendProtocol):
    """This class offers a cache backend that stores values in a `dict`.

    In a production system you probably should use Redis or MemCached
    instead.
    """

    @dataclass()
    class CacheObject:
        """A container class."""

        value: Any
        expiration: datetime

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Any:
        """Retrieve value from cache corresponding to the given key.

        Args:
            key (str): name of cached value.

        Returns:
            Cached value, or `None`.
        """
        cache_obj = cast("Optional[SimpleCacheBackend.CacheObject]", self._store.get(key))
        if cache_obj:
            if cache_obj.expiration >= datetime.now():
                return cache_obj.value
            self.delete(key)
        return None

    def set(self, key: str, value: Any, expiration: int) -> None:
        """Set a value in cache for a given key with a given expiration in
        seconds.

        Args:
            key (str): key to cache `value` under.
            value (str): the value to be cached.
            expiration (int): expiration of cached value in seconds.
        """
        self._store[key] = SimpleCacheBackend.CacheObject(
            value=value, expiration=datetime.now() + timedelta(seconds=expiration)
        )

    def delete(self, key: str) -> None:
        """Remove a value from the cache for a given key.

        Args:
            key (str): key to be deleted from the cache.
        """
        self._store.pop(key, None)
