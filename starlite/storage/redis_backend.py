from __future__ import annotations

from datetime import timedelta
from typing import cast

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from starlite.exceptions import ImproperlyConfiguredException
from starlite.types import Empty, EmptyType

from .base import StorageBackend


class RedisStorageBackend(StorageBackend):
    __slots__ = ("_redis",)

    @property
    def key_prefix(self) -> str:
        return f"{self.namespace}:" if self.namespace else ""

    def make_key(self, key: str) -> str:
        return self.key_prefix + key

    def __init__(self, redis: Redis, namespace: str | None | EmptyType = Empty) -> None:
        self._redis = redis
        self.namespace = "STARLITE" if namespace is Empty else namespace

        # script to get and renew a key in one atomic step
        self._get_and_renew_script = self._redis.register_script(
            b"""
        local key = KEYS[1]
        local renew = tonumber(ARGV[1])

        local data = redis.call('GET', key)
        local ttl = redis.call('TTL', key)

        if ttl > 0 then
            redis.call('EXPIRE', key, renew)
        end

        return data
        """
        )

        # script to delete all keys in the namespace
        self._delete_all_script = self._redis.register_script(
            b"""
        local cursor = 0

        repeat
            local result = redis.call('SCAN', cursor, 'MATCH', ARGV[1])
            for _,key in ipairs(result[2]) do
                redis.call('UNLINK', key)
            end
            cursor = tonumber(result[1])
        until cursor == 0
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

    async def set(self, key: str, value: bytes, expires_in: int | timedelta | None = None) -> None:
        await self._redis.set(self.make_key(key), value, ex=expires_in)

    async def get(self, key: str, renew_for: int | timedelta | None = None) -> bytes | None:
        key = self.make_key(key)
        if renew_for:
            if isinstance(renew_for, timedelta):
                renew_for = renew_for.seconds
            data = await self._get_and_renew_script(keys=[key], args=[renew_for])
            return cast("bytes | None", data)
        return await self._redis.get(key)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self.make_key(key))

    async def delete_all(self) -> None:
        if not self.namespace:
            raise ImproperlyConfiguredException("Cannot perform delete operation: key_prefix not set")

        await self._delete_all_script(keys=[], args=[self.key_prefix + "*"])

    async def exists(self, key: str) -> bool:
        return await self._redis.exists(self.make_key(key)) == 1

    async def expires_in(self, key: str) -> int | None:
        ttl = await self._redis.ttl(key)
        if ttl == -2:
            return None
        return ttl
