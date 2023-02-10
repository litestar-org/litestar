from __future__ import annotations

from aiomcache import Client

from starlite.types import Empty, EmptyType

from .base import NamespacedStorageBackend


class MemcachedStorageBackend(NamespacedStorageBackend):
    __slots__ = ("_memcached",)

    def __init__(self, memcached: Client, namespace: str | None | EmptyType = Empty) -> None:
        self._memcached = memcached
        super().__init__(namespace=namespace)

    @classmethod
    def with_client(
        cls,
        host: str,
        *,
        port: int = 11211,
        pool_size: int = 2,
        pool_minsize: int | None = None,
        namespace: str | None | EmptyType = Empty,
    ) -> MemcachedStorageBackend:
        return cls(
            memcached=Client(host=host, port=port, pool_size=pool_size, pool_minsize=pool_minsize), namespace=namespace
        )

    def with_namespace(self, namespace: str) -> MemcachedStorageBackend:
        return type(self)(memcached=self._memcached, namespace=f"STARLITE_{namespace}")

    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        await self._memcached.set(self.make_key(key).encode("utf-8"), value, exptime=expires or 0)

    async def get(self, key: str) -> bytes | None:
        return await self._memcached.get(self.make_key(key).encode("utf-8"))

    async def delete(self, key: str) -> None:
        await self._memcached.delete(self.make_key(key).encode("utf-8"))
