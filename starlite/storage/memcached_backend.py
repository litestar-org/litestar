from __future__ import annotations

from aiomcache import Client

from .base import StorageBackend


class MemcachedStorageBackend(StorageBackend):
    __slots__ = ("_memcached",)

    def __init__(self, memcached: Client, key_prefix: str | None = None) -> None:
        super().__init__(key_prefix=key_prefix)
        self._memcached = memcached

    @classmethod
    def with_client(
        cls,
        host: str,
        *,
        port: int = 11211,
        pool_size: int = 2,
        pool_minsize: int | None = None,
    ) -> MemcachedStorageBackend:
        return cls(memcached=Client(host=host, port=port, pool_size=pool_size, pool_minsize=pool_minsize))

    def with_key_prefix(self, key_prefix: str) -> MemcachedStorageBackend:
        return type(self)(memcached=self._memcached, key_prefix=key_prefix)

    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        await self._memcached.set(self.make_key(key).encode("utf-8"), value, exptime=expires or 0)

    async def get(self, key: str) -> bytes | None:
        return await self._memcached.get(self.make_key(key).encode("utf-8"))

    async def delete(self, key: str) -> None:
        await self._memcached.delete(self.make_key(key).encode("utf-8"))
