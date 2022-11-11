from typing import TYPE_CHECKING, Any, Optional, Protocol, overload, runtime_checkable

from anyio import Lock

from starlite.utils import is_async_callable

if TYPE_CHECKING:
    from starlite.connection import Request
    from starlite.types import CacheKeyBuilder


@runtime_checkable
class CacheBackendProtocol(Protocol):  # pragma: no cover
    """Protocol for cache backends."""

    @overload  # type: ignore[misc]
    def get(self, key: str) -> Any:  # pyright: ignore
        """Overload."""
        ...

    async def get(self, key: str) -> Any:
        """Retrieve a value from cache corresponding to the given key.

        Args:
            key: name of cached value.

        Returns:
            Cached value if existing else `None`.
        """

    @overload  # type: ignore[misc]
    def set(self, key: str, value: Any, expiration: int) -> Any:  # pyright: ignore
        """Overload."""
        ...

    async def set(self, key: str, value: Any, expiration: int) -> Any:
        """Set a value in cache for a given key for a duration determined by expiration.

        Args:
            key: key to cache `value` under.
            value: the value to be cached.
            expiration: expiration of cached value in seconds.

        Notes:
            - expiration is in seconds.
            - return value is not used by Starlite internally.

        Returns:
            Any
        """

    @overload  # type: ignore[misc]
    def delete(self, key: str) -> Any:  # pyright: ignore
        """Overload."""
        ...

    async def delete(self, key: str) -> Any:
        """Delete a value from the cache and remove the given key.

        Args:
            key: key to be deleted from the cache.

        Notes:
            - return value is not used by Starlite internally.

        Returns:
            Any
        """


class Cache:
    """Wrapper for a provided CacheBackend that ensures it is called in an async and thread-safe fashion.

    This enables the use of normal sync libraries (such as the standard Redis python client) for caching responses.
    """

    __slots__ = ("backend", "lock", "default_expiration", "key_builder")

    def __init__(
        self, backend: CacheBackendProtocol, default_expiration: int, cache_key_builder: "CacheKeyBuilder"
    ) -> None:
        """Initialize `Cache`.

        Args:
            backend: A class instance fulfilling the Starlite [CacheBackendProtocol][starlite.cache.base.CacheBackendProtocol].
            default_expiration: Default value (in seconds) for cache expiration.
            cache_key_builder: A function that receives a request object and returns a unique cache key.
        """
        self.backend = backend
        self.default_expiration = default_expiration
        self.key_builder = cache_key_builder
        self.lock = Lock()

    async def get(self, key: str) -> Any:
        """Proxy 'self.backend.get'.

        Args:
            key: name of cached value.

        Returns:
            Cached value if existing else `None`.
        """
        if is_async_callable(self.backend.get):  # pyright: ignore
            return await self.backend.get(key)

        async with self.lock:
            return self.backend.get(key)

    async def set(self, key: str, value: Any, expiration: Optional[int] = None) -> Any:
        """Proxy 'self.backend.set'.

        Args:
            key: key to cache `value` under.
            value: the value to be cached.
            expiration: expiration of cached value in seconds.

        Notes:
            - expiration is in seconds.
            - return value is not used by Starlite internally.

        Returns:
            Any
        """
        if is_async_callable(self.backend.set):  # pyright: ignore
            return await self.backend.set(key, value, expiration or self.default_expiration)

        async with self.lock:
            return self.backend.set(key, value, expiration or self.default_expiration)

    async def delete(self, key: str) -> Any:
        """Proxy 'self.backend.delete'.

        Args:
            key: key to be deleted from the cache.

        Notes:
            - return value is not used by Starlite internally.

        Returns:
            Any
        """
        if is_async_callable(self.backend.delete):  # pyright: ignore
            return await self.backend.delete(key)

        async with self.lock:
            return self.backend.delete(key)

    def build_cache_key(self, request: "Request", cache_key_builder: Optional["CacheKeyBuilder"]) -> str:
        """Construct a unique cache key from the request instance.

        Args:
            request: A [Request][starlite.connection.Request] instance.
            cache_key_builder: An optional [CacheKeyBuilder][starlite.types.CacheKeyBuilder] function.

        Returns:
            A unique cache key string.
        """
        key_builder = cache_key_builder or self.key_builder
        return key_builder(request)
