from __future__ import annotations

from typing import cast

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

        # script to get and possibly renew a key in one atomic step
        self._get_and_renew_script = self._redis.register_script(
            b"""
        local key = KEYS[1]
        local renew = tonumber(ARGV[1])
        local data = redis.call('GET', key)

        if renew > 0 then
            local ttl = redis.call('TTL', key)
            if ttl > 0 then
                redis.call('EXPIRE', key, renew)
            end
        end

        return data
        """
        )

        # script to delete all keys in the namespace
        self._delete_all_script = self._redis.register_script(
            b"""
        local cursor = 0
        local count_deleted = 0

        repeat
            local result = redis.call('SCAN', cursor, 'MATCH', ARGV[1])
            for _,key in ipairs(result[2]) do
                redis.call('UNLINK', key)
                count_deleted = count_deleted + 1
            end
            cursor = tonumber(result[1])
        until cursor == 0

        return count_deleted
        """
        )

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

    async def get(self, key: str, renew: int | None = None) -> bytes | None:
        key = self.make_key(key)
        data = await self._get_and_renew_script(keys=[key], args=[0 if renew is None else renew])
        return cast("bytes | None", data)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self.make_key(key))

    async def delete_all(self) -> int:
        if not self.namespace:
            raise ImproperlyConfiguredException("Cannot perform delete operation: key_prefix not set")

        count = await self._delete_all_script(keys=[], args=[self.key_prefix + "*"])
        return cast("int", count)
