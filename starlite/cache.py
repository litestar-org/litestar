from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlite import Request
    from starlite.storage.base import StorageBackend
    from starlite.types import CacheKeyBuilder


class Cache:
    __slots__ = ("backend", "default_expiration", "key_builder")

    def __init__(self, backend: StorageBackend, default_expiration: int, cache_key_builder: CacheKeyBuilder) -> None:
        self.backend = backend
        self.default_expiration = default_expiration
        self.key_builder = cache_key_builder

    async def get(self, key: str) -> bytes | None:
        return await self.backend.get(key)

    async def set(self, key: str, value: Any, expiration: int | None = None) -> None:
        await self.backend.set(key, value, expiration or self.default_expiration)

    async def delete(self, key: str) -> Any:
        await self.backend.delete(key)

    def build_cache_key(self, request: Request, cache_key_builder: CacheKeyBuilder | None = None) -> str:
        key_builder = cache_key_builder or self.key_builder
        return key_builder(request)
