from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ("Cache",)


if TYPE_CHECKING:
    from starlite import Request
    from starlite.storage.base import Storage
    from starlite.types import CacheKeyBuilder


class Cache:
    """Asynchronous cache"""

    __slots__ = {
        "backend": "Storage backend",
        "default_expiration": "Default expiration time",
        "key_builder": "A :class:`CacheKeyBuilder <.types.CacheKeyBuilder>`",
    }

    def __init__(self, backend: Storage, default_expiration: int, cache_key_builder: CacheKeyBuilder) -> None:
        """Initialize cache

        Args:
            backend: Storage backend
            default_expiration: Default expiration
            cache_key_builder: Callable to create cache keys from requests
        """
        self.backend = backend
        self.default_expiration = default_expiration
        self.key_builder = cache_key_builder

    async def get(self, key: str) -> bytes | None:
        """Get a value from the cache"""
        return await self.backend.get(key)

    async def set(self, key: str, value: Any, expiration: int | None = None) -> None:
        """Set a value in the cache"""
        await self.backend.set(key, value, expiration or self.default_expiration)

    async def delete(self, key: str) -> Any:
        """Delete a value from the cache"""
        await self.backend.delete(key)

    def build_cache_key(self, request: Request, cache_key_builder: CacheKeyBuilder | None = None) -> str:
        """Create a cache key from a request. If ``cache_key_builder`` is not passed, :attr:`Cache.key_builder` will be
        used
        """
        key_builder = cache_key_builder or self.key_builder
        return key_builder(request)
