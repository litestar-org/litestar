from __future__ import annotations

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from ..exceptions import ImproperlyConfiguredException
from .base import StorageBackend


class RedisStorageBackend(StorageBackend):
    __slots__ = ("_redis",)

    def __init__(self, redis: Redis, key_prefix: str | None = None) -> None:
        super().__init__(key_prefix=key_prefix)
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
    ) -> RedisStorageBackend:
        pool = ConnectionPool.from_url(
            url=url,
            db=db,
            decode_responses=False,
            port=port,
            username=username,
            password=password,
        )
        return cls(redis=Redis(connection_pool=pool))

    def with_key_prefix(self, key_prefix: str) -> RedisStorageBackend:
        return type(self)(redis=self._redis, key_prefix=key_prefix)

    async def set(self, key: str, value: bytes, expires: int | None = None) -> None:
        await self._redis.set(self.make_key(key), value, ex=expires)

    async def get(self, key: str) -> bytes | None:
        return await self._redis.get(self.make_key(key))

    async def delete(self, key: str) -> None:
        await self._redis.delete(self.make_key(key))

    async def delete_all(self) -> None:
        if not self.key_prefix:
            raise ImproperlyConfiguredException("Cannot perform delete operation: key_prefix not set")

        pattern = f"{self.key_prefix}:*"
        cursor: int | None = None
        while (cursor is None) or cursor > 0:
            cursor, keys = await self._redis.scan(cursor=cursor or 0, match=pattern, count=3000)
            if keys:
                await self._redis.delete(*keys)
