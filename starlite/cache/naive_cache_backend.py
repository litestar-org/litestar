from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, cast

from starlite.cache.base import CacheBackendProtocol


class SimpleCacheBackend(CacheBackendProtocol):
    """
    This class offers a cache backend that stores values in a dict.

    In a production system you probably should use Redis or MemCached instead.
    """

    @dataclass(init=True)
    class CacheObject:
        """
        A container class
        """

        value: Any
        expiration: datetime

    def __init__(self) -> None:
        self._store: Dict[str, Any] = {}

    def get(self, key: str) -> Any:
        """
        Retrieve a value for a given key
        """
        cache_obj = cast(Optional[SimpleCacheBackend.CacheObject], self._store.get(key))
        if cache_obj:
            if cache_obj.expiration >= datetime.now():
                return cache_obj.value
            self.delete(key)
        return None

    def set(self, key: str, value: Any, expiration: int) -> None:
        """
        Set a value for a given key
        """
        self._store[key] = SimpleCacheBackend.CacheObject(
            value=value, expiration=datetime.now() + timedelta(seconds=expiration)
        )

    def delete(self, key: str) -> None:
        """
        Remove a value for a given key
        """
        self._store.pop(key, None)
