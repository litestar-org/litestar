from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Awaitable, Dict, Optional, Protocol, cast, overload

from typing_extensions import runtime_checkable


@runtime_checkable
class CacheBackendProtocol(Protocol):  # pragma: no cover
    @overload  # type: ignore[misc]
    def get(self, key: str) -> Any:
        ...

    async def get(self, key: str) -> Awaitable[Any]:
        """
        Retrieve a valued from cache corresponding to the given key
        """
        ...

    @overload  # type: ignore[misc]
    def set(self, key: str, value: Any, expiration: int) -> Any:
        ...

    async def set(self, key: str, value: Any, expiration: int) -> Awaitable[Any]:
        """
        Set a value in cache for a given key with a given expiration in seconds
        """
        ...

    @overload  # type: ignore[misc]
    def delete(self, key: str) -> Any:
        ...

    async def delete(self, key: str) -> Awaitable[Any]:
        """
        Remove a value from the cache for a given key
        """
        ...


class NaiveCacheBackend(CacheBackendProtocol):
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
        cache_obj = cast(Optional[NaiveCacheBackend.CacheObject], self._store.get(key))
        if cache_obj:
            if cache_obj.expiration >= datetime.now():
                return cache_obj.value
            self.delete(key)
        return None

    def set(self, key: str, value: Any, expiration: int) -> None:
        """
        Set a value for a given key
        """
        self._store[key] = NaiveCacheBackend.CacheObject(
            value=value, expiration=datetime.now() + timedelta(seconds=expiration)
        )

    def delete(self, key: str) -> None:
        """
        Remove a value for a given key
        """
        self._store.pop(key, None)
