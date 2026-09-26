from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import timedelta
from typing import TYPE_CHECKING, Literal, cast, overload

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool

from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import Empty, EmptyType
from litestar.utils.empty import value_or_default

from .base import NamespacedStore

if TYPE_CHECKING:
    from types import TracebackType

    from redis.asyncio.connection import Connection

__all__ = ("RedisStore",)


# script to get and renew a key in one atomic step
_GET_AND_RENEW_SCRIPT = b"""
local key = KEYS[1]
local renew = tonumber(ARGV[1])

local data = redis.call('GET', key)
local ttl = redis.call('TTL', key)

if ttl > 0 then
    redis.call('EXPIRE', key, renew)
end

return data
"""

# script to delete all keys in the namespace
_DELETE_ALL_SCRIPT = b"""
local cursor = 0

repeat
    local result = redis.call('SCAN', cursor, 'MATCH', ARGV[1])
    for _,key in ipairs(result[2]) do
        redis.call('UNLINK', key)
    end
    cursor = tonumber(result[1])
until cursor == 0
"""


def _to_seconds(value: int | timedelta) -> int:
    return int(value.total_seconds()) if isinstance(value, timedelta) else value


class _RedisStrategy(ABC):
    """Internal backend performing the actual Redis commands for :class:`RedisStore`."""

    __slots__ = ("_redis", "namespace")

    def __init__(self, redis: Redis, namespace: str | None) -> None:
        self._redis = redis
        self.namespace = namespace

    @abstractmethod
    async def set(self, key: str, value: bytes, expires_in: int | timedelta | None, keep_ttl: bool) -> None:
        raise NotImplementedError

    @abstractmethod
    async def get(self, key: str, renew_for: int | timedelta | None) -> bytes | None:
        raise NotImplementedError

    @abstractmethod
    async def delete(self, key: str) -> None:
        raise NotImplementedError

    @abstractmethod
    async def delete_all(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def expires_in(self, key: str) -> int | None:
        raise NotImplementedError


class _KeysStrategy(_RedisStrategy):
    """Store each value under its own ``<namespace>:<key>`` Redis key."""

    __slots__ = ("_delete_all_script", "_get_and_renew_script")

    def __init__(self, redis: Redis, namespace: str | None) -> None:
        super().__init__(redis, namespace)
        # script to get and renew a key in one atomic step
        self._get_and_renew_script = redis.register_script(_GET_AND_RENEW_SCRIPT)
        # script to delete all keys in the namespace
        self._delete_all_script = redis.register_script(_DELETE_ALL_SCRIPT)

    def _make_key(self, key: str) -> str:
        prefix = f"{self.namespace}:" if self.namespace else ""
        return prefix + key

    async def set(self, key: str, value: bytes, expires_in: int | timedelta | None, keep_ttl: bool) -> None:
        await self._redis.set(self._make_key(key), value, ex=expires_in, keepttl=keep_ttl)

    async def get(self, key: str, renew_for: int | timedelta | None) -> bytes | None:
        redis_key = self._make_key(key)
        if renew_for:
            renew_for = _to_seconds(renew_for)
            data = await self._get_and_renew_script(keys=[redis_key], args=[renew_for])
            return cast("bytes | None", data)
        return await self._redis.get(redis_key)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self._make_key(key))

    async def delete_all(self) -> None:
        await self._delete_all_script(keys=[], args=[f"{self.namespace}*:*"])

    async def exists(self, key: str) -> bool:
        return await self._redis.exists(self._make_key(key)) == 1

    async def expires_in(self, key: str) -> int | None:
        ttl = await self._redis.ttl(self._make_key(key))
        return None if ttl == -2 else ttl


class RedisStore(NamespacedStore):
    """Redis based, thread and process safe asynchronous key/value store."""

    __slots__ = ("_redis", "_strategy", "handle_client_shutdown")

    def __init__(
        self, redis: Redis, namespace: str | None | EmptyType = Empty, handle_client_shutdown: bool = False
    ) -> None:
        """Initialize :class:`RedisStore`

        Args:
            redis: An :class:`redis.asyncio.Redis` instance
            namespace: A key prefix to simulate a namespace in redis. If not given,
                defaults to ``LITESTAR``. Namespacing can be explicitly disabled by passing
                ``None``. This will make :meth:`.delete_all` unavailable.
            handle_client_shutdown: If ``True``, handle the shutdown of the `redis` instance automatically during the store's lifespan. Should be set to `True` unless the shutdown is handled externally
        """
        self._redis = redis
        self.namespace: str | None = value_or_default(namespace, "LITESTAR")
        self.handle_client_shutdown = handle_client_shutdown

        self._strategy: _RedisStrategy = _KeysStrategy(redis, self.namespace)

    async def _shutdown(self) -> None:
        if self.handle_client_shutdown:
            await self._redis.aclose(close_connection_pool=True)  # type: ignore[attr-defined]

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self._shutdown()

    @classmethod
    def with_client(
        cls,
        url: str = "redis://localhost:6379",
        *,
        db: int | None = None,
        port: int | None = None,
        username: str | None = None,
        password: str | None = None,
        namespace: str | None | EmptyType = Empty,
    ) -> RedisStore:
        """Initialize a :class:`RedisStore` instance with a new class:`redis.asyncio.Redis` instance.

        Args:
            url: Redis URL to connect to
            db: Redis database to use
            port: Redis port to use
            username: Redis username to use
            password: Redis password to use
            namespace: Virtual key namespace to use
        """
        pool: ConnectionPool[Connection] = ConnectionPool.from_url(
            url=url,
            db=db,
            decode_responses=False,
            port=port,
            username=username,
            password=password,
        )
        return cls(
            redis=Redis(connection_pool=pool),
            namespace=namespace,
            handle_client_shutdown=True,
        )

    def with_namespace(self, namespace: str) -> RedisStore:
        """Return a new :class:`RedisStore` with a nested virtual key namespace.
        The current instances namespace will serve as a prefix for the namespace, so it
        can be considered the parent namespace.
        """
        return type(self)(
            redis=self._redis,
            namespace=f"{self.namespace}_{namespace}" if self.namespace else namespace,
            handle_client_shutdown=self.handle_client_shutdown,
        )

    @overload
    async def set(
        self,
        key: str,
        value: str | bytes,
        expires_in: int | timedelta | None = ...,
        keep_ttl: Literal[False] = ...,
    ) -> None: ...

    @overload
    async def set(
        self,
        key: str,
        value: str | bytes,
        expires_in: None = ...,
        *,
        keep_ttl: Literal[True],
    ) -> None: ...

    async def set(
        self,
        key: str,
        value: str | bytes,
        expires_in: int | timedelta | None = None,
        keep_ttl: bool = False,
    ) -> None:
        """Set a value.

        Args:
            key: Key to associate the value with
            value: Value to store
            expires_in: Time in seconds before the key is considered expired
            keep_ttl: If ``True``, the TTL of the key will not be changed. If ``False``, the TTL of the key will be set to the value of ``expires_in``

        Raises:
            ValueError: If both ``expires_in`` and ``keep_ttl`` are set, as these options are mutually exclusive

        Returns:
            ``None``
        """
        if expires_in is not None and keep_ttl:
            raise ValueError("Cannot set both 'expires_in' and 'keep_ttl': these options are mutually exclusive")
        if isinstance(value, str):
            value = value.encode("utf-8")
        await self._strategy.set(key, value, expires_in, keep_ttl)

    async def get(self, key: str, renew_for: int | timedelta | None = None) -> bytes | None:
        """Get a value.

        Args:
            key: Key associated with the value
            renew_for: If given and the value had an initial expiry time set, renew the
                expiry time for ``renew_for`` seconds. If the value has not been set
                with an expiry time this is a no-op. Atomicity of this step is guaranteed
                by using a lua script to execute fetch and renewal. If ``renew_for`` is
                not given, the script will be bypassed so no overhead will occur

        Returns:
            The value associated with ``key`` if it exists and is not expired, else
            ``None``
        """
        return await self._strategy.get(key, renew_for)

    async def delete(self, key: str) -> None:
        """Delete a value.

        If no such key exists, this is a no-op.

        Args:
            key: Key of the value to delete
        """
        await self._strategy.delete(key)

    async def delete_all(self) -> None:
        """Delete all stored values in the virtual key namespace.

        Raises:
            ImproperlyConfiguredException: If no namespace was configured
        """
        if not self.namespace:
            raise ImproperlyConfiguredException("Cannot perform delete operation: No namespace configured")

        await self._strategy.delete_all()

    async def exists(self, key: str) -> bool:
        """Check if a given ``key`` exists."""
        return await self._strategy.exists(key)

    async def expires_in(self, key: str) -> int | None:
        """Get the time in seconds ``key`` expires in. If no such ``key`` exists or no
        expiry time was set, return ``None``.
        """
        return await self._strategy.expires_in(key)
