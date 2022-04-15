from typing import Any

from typing_extensions import Awaitable, Protocol, overload, runtime_checkable


@runtime_checkable
class CacheBackendProtocol(Protocol):  # pragma: no cover
    @overload  # type: ignore[misc]
    def get(self, key: str) -> Any:
        ...

    async def get(self, key: str) -> Awaitable[Any]:
        """
        Retrieve a valued from cache corresponding to the given key
        """

    @overload  # type: ignore[misc]
    def set(self, key: str, value: Any, expiration: int) -> Any:
        ...

    async def set(self, key: str, value: Any, expiration: int) -> Awaitable[Any]:
        """
        Set a value in cache for a given key with a given expiration in seconds
        """

    @overload  # type: ignore[misc]
    def delete(self, key: str) -> Any:
        ...

    async def delete(self, key: str) -> Awaitable[Any]:
        """
        Remove a value from the cache for a given key
        """
