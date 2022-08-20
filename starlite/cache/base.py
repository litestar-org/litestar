from typing import Any, Awaitable, overload

from typing_extensions import Protocol, runtime_checkable


@runtime_checkable
class CacheBackendProtocol(Protocol):  # pragma: no cover
    @overload  # type: ignore[misc]
    def get(self, key: str) -> Any:
        ...

    async def get(self, key: str) -> Awaitable[Any]:
        """Retrieve value from cache corresponding to the given key.

        Args:
            key (str): name of cached value.

        Returns:
            Cached value.
        """

    @overload  # type: ignore[misc]
    def set(self, key: str, value: Any, expiration: int) -> Any:
        ...

    async def set(self, key: str, value: Any, expiration: int) -> Awaitable[Any]:
        """Set a value in cache for a given key with a given expiration in
        seconds.

        Args:
            key (str): key to cache `value` under.
            value (str): the value to be cached.
            expiration (int): expiration of cached value in seconds.

        Returns:
            Return value is ignored by Starlite.
        """

    @overload  # type: ignore[misc]
    def delete(self, key: str) -> Any:
        ...

    async def delete(self, key: str) -> Awaitable[Any]:
        """Remove a value from the cache for a given key.

        Args:
            key (str): key to be deleted from the cache.

        Returns:
            No return value requirement.
        """
