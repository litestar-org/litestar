from __future__ import annotations

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from starlite.exceptions import ImproperlyConfiguredException
from starlite.types import Empty, EmptyType

from .base import NamespacedStorageBackend


class RedisStorageBackend(NamespacedStorageBackend):
    __slots__ = ("_redis",)

    def __init__(self, redis: Redis, namespace: str | None | EmptyType = Empty) -> None:
        super().__init__(namespace=namespace)
        self._redis = redis

    @classmethod
    def with_client(
        cls,
        url: str,
        *,
        db: int | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        namespace: str | None | EmptyType = Empty,
    ) -> RedisStorageBackend:
        pool = ConnectionPool.from_url(
            url=url,
            db=db,
            decode_responses=False,
            port=port,
            username=username,
            password=password,
        )
        return cls(redis=Redis(connection_pool=pool), namespace=namespace)

    def with_namespace(self, namespace: str) -> RedisStorageBackend:
        return type(self)(redis=self._redis, namespace=f"STARLITE_{namespace}")

    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        await self._redis.set(self.make_key(key), value, ex=expires)

    async def get(self, key: str) -> bytes | None:
        return await self._redis.get(self.make_key(key))

    async def delete(self, key: str) -> None:
        await self._redis.delete(self.make_key(key))

    async def delete_all(self) -> None:
        if not self.namespace:
            raise ImproperlyConfiguredException("Cannot perform delete operation: key_prefix not set")

        pattern = f"{self.namespace}:*"
        cursor: int | None = None
        while (cursor is None) or cursor > 0:
            cursor, keys = await self._redis.scan(cursor=cursor or 0, match=pattern, count=3000)
            if keys:
                await self._redis.delete(*keys)
