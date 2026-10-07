from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING, Literal, cast, overload

from redis.asyncio import Redis
from redis.asyncio.connection import ConnectionPool
from redis.exceptions import RedisError

from litestar.exceptions import ImproperlyConfiguredException
from litestar.types import Empty, EmptyType
from litestar.utils.empty import value_or_default

from .base import NamespacedStore

if TYPE_CHECKING:
    from types import TracebackType

    from redis.asyncio.connection import Connection

__all__ = ("RedisStore", "RedisStoreNamespaceStrategy")


RedisStoreNamespaceStrategy = Literal["keys", "hash", "auto"]


_HASH_FIELD_EXPIRATION_MIN_VERSION = (7, 4)
_HASH_FIELD_EXPIRATION_COMMANDS_VERSION = (8, 0)
_ResolvedNamespaceStrategy = Literal["keys", "hash"]


def _escape_redis_glob(value: str) -> str:
    """Escape glob metacharacters in a value used with Redis ``SCAN MATCH``."""
    return value.replace("\\", "\\\\").replace("*", "\\*").replace("?", "\\?").replace("[", "\\[").replace("]", "\\]")


class RedisStore(NamespacedStore):
    """Redis based, thread and process safe asynchronous key/value store."""

    __slots__ = (
        "_delete_all_script",
        "_delete_hash_children_script",
        "_get_and_renew_script",
        "_hash_get_and_renew_script",
        "_hash_get_and_renew_with_hgetex_script",
        "_hash_set_keep_ttl_script",
        "_hash_set_with_expiry_script",
        "_redis",
        "_redis_version",
        "_resolved_namespace_strategy",
        "handle_client_shutdown",
        "namespace_strategy",
    )

    def __init__(
        self,
        redis: Redis,
        namespace: str | EmptyType | None = Empty,
        handle_client_shutdown: bool = False,
        namespace_strategy: RedisStoreNamespaceStrategy = "keys",
    ) -> None:
        """Initialize :class:`RedisStore`

        Args:
            redis: An :class:`redis.asyncio.Redis` instance
            namespace: A key prefix to simulate a namespace in redis. If not given,
                defaults to ``LITESTAR``. Namespacing can be explicitly disabled by passing
                ``None``. This will make :meth:`.delete_all` unavailable.
            handle_client_shutdown: If ``True``, handle the shutdown of the `redis` instance automatically during the store's lifespan. Should be set to `True` unless the shutdown is handled externally
            namespace_strategy: Storage layout to use. ``"keys"`` preserves the existing
                key-per-value layout, ``"hash"`` stores fields in a Redis hash named after
                the namespace, and ``"auto"`` selects based on the Redis server version.
        """
        if namespace_strategy not in ("keys", "hash", "auto"):
            raise ValueError("namespace_strategy must be one of 'keys', 'hash', or 'auto'")
        self._redis = redis
        self.namespace: str | None = value_or_default(namespace, "LITESTAR")
        if namespace_strategy == "hash" and not self.namespace:
            raise ImproperlyConfiguredException("The hash namespace strategy requires a namespace")
        self.handle_client_shutdown = handle_client_shutdown
        self.namespace_strategy: RedisStoreNamespaceStrategy = namespace_strategy
        self._redis_version: tuple[int, int] | None = None
        self._resolved_namespace_strategy: _ResolvedNamespaceStrategy | None = (
            "keys" if self.namespace_strategy == "keys" or not self.namespace else None
        )

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

        self._hash_set_with_expiry_script = self._redis.register_script(
            b"""
        local hash = KEYS[1]
        local field = ARGV[1]
        local value = ARGV[2]
        local expires_ms = tonumber(ARGV[3])

        redis.call('HSET', hash, field, value)
        return redis.call('HPEXPIRE', hash, expires_ms, 'FIELDS', 1, field)
        """
        )

        self._hash_set_keep_ttl_script = self._redis.register_script(
            b"""
        local hash = KEYS[1]
        local field = ARGV[1]
        local value = ARGV[2]
        local ttl = redis.call('HPTTL', hash, 'FIELDS', 1, field)[1]

        redis.call('HSET', hash, field, value)
        if ttl >= 0 then
            redis.call('HPEXPIRE', hash, ttl, 'FIELDS', 1, field)
        end
        """
        )

        self._hash_get_and_renew_script = self._redis.register_script(
            b"""
        local hash = KEYS[1]
        local field = ARGV[1]
        local renew = tonumber(ARGV[2])
        local data = redis.call('HGET', hash, field)
        local ttl = redis.call('HPTTL', hash, 'FIELDS', 1, field)[1]

        if ttl > 0 then
            redis.call('HPEXPIRE', hash, renew, 'FIELDS', 1, field)
        end
        return data
        """
        )

        self._hash_get_and_renew_with_hgetex_script = self._redis.register_script(
            b"""
        local hash = KEYS[1]
        local field = ARGV[1]
        local renew = tonumber(ARGV[2])
        -- Check TTL and renewal atomically so persistent fields remain persistent.
        local ttl = redis.call('HPTTL', hash, 'FIELDS', 1, field)[1]

        if ttl > 0 then
            return redis.call('HGETEX', hash, 'PX', renew, 'FIELDS', 1, field)[1]
        end
        return redis.call('HGET', hash, field)
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

        self._delete_hash_children_script = self._redis.register_script(
            b"""
        if #KEYS == 1 then
            redis.call('UNLINK', KEYS[1])
        end

        local cursor = 0

        repeat
            local result = redis.call('SCAN', cursor, 'MATCH', ARGV[1])
            for _,key in ipairs(result[2]) do
                if redis.call('TYPE', key).ok == 'hash' then
                    redis.call('UNLINK', key)
                end
            end
            cursor = tonumber(result[1])
        until cursor == 0
        """
        )

    async def __aenter__(self) -> None:
        await self._resolve_namespace_strategy()

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
        namespace: str | EmptyType | None = Empty,
        namespace_strategy: RedisStoreNamespaceStrategy = "keys",
    ) -> RedisStore:
        """Initialize a :class:`RedisStore` instance with a new class:`redis.asyncio.Redis` instance.

        Args:
            url: Redis URL to connect to
            db: Redis database to use
            port: Redis port to use
            username: Redis username to use
            password: Redis password to use
            namespace: Virtual key namespace to use
            namespace_strategy: Storage layout to use. See :class:`RedisStore`.
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
            namespace_strategy=namespace_strategy,
        )

    def with_namespace(self, namespace: str) -> RedisStore:
        """Return a new :class:`RedisStore` with a nested virtual key namespace.
        The current instances namespace will serve as a prefix for the namespace, so it
        can be considered the parent namespace.
        """
        store = type(self)(
            redis=self._redis,
            namespace=f"{self.namespace}_{namespace}" if self.namespace else namespace,
            handle_client_shutdown=self.handle_client_shutdown,
            namespace_strategy=self.namespace_strategy,
        )
        if self._redis_version is not None:
            store._redis_version = self._redis_version
            store._resolved_namespace_strategy = self._resolved_namespace_strategy
        return store

    def _make_key(self, key: str) -> str:
        prefix = f"{self.namespace}:" if self.namespace else ""
        return prefix + key

    async def _resolve_namespace_strategy(self) -> _ResolvedNamespaceStrategy:
        """Resolve and validate the configured namespace storage strategy."""
        if self._resolved_namespace_strategy is not None:
            return self._resolved_namespace_strategy

        try:
            server_info = await self._redis.info("server")
            version_text = cast("str", server_info["redis_version"])
            major, minor, *_ = version_text.split(".")
            self._redis_version = (int(major), int(minor))
        except (ConnectionError, KeyError, OSError, RedisError, TypeError, ValueError):
            if self.namespace_strategy == "hash":
                raise ImproperlyConfiguredException(
                    "The hash namespace strategy requires a Redis server version"
                ) from None
            self._resolved_namespace_strategy = "keys"
            return self._resolved_namespace_strategy

        if self._redis_version < _HASH_FIELD_EXPIRATION_MIN_VERSION:
            if self.namespace_strategy == "hash":
                raise ImproperlyConfiguredException(
                    f"The hash namespace strategy requires Redis 7.4 or later (server version: {version_text})"
                )
            self._resolved_namespace_strategy = "keys"
        else:
            self._resolved_namespace_strategy = "hash"
        return self._resolved_namespace_strategy

    @staticmethod
    def _expiry_seconds(value: int | timedelta) -> int:
        """Convert an expiry value to whole seconds."""
        return int(value.total_seconds()) if isinstance(value, timedelta) else value

    @staticmethod
    def _expiry_milliseconds(value: int | timedelta) -> int:
        """Convert an expiry value to whole milliseconds."""
        return int(value.total_seconds() * 1000) if isinstance(value, timedelta) else value * 1000

    async def _set_hash_value(
        self,
        key: str,
        value: bytes,
        expires_in: int | timedelta | None,
        keep_ttl: bool,
    ) -> None:
        """Set a value using Redis hash field expiration commands."""
        hash_key = cast("str", self.namespace)
        redis_version = cast("tuple[int, int]", self._redis_version)

        if expires_in is not None:
            expires_in_ms = self._expiry_milliseconds(expires_in)
            if expires_in_ms <= 0:
                raise ValueError("'expires_in' must be a positive duration")
            if redis_version >= _HASH_FIELD_EXPIRATION_COMMANDS_VERSION:
                await self._redis.hsetex(  # type: ignore[attr-defined]
                    hash_key, key=key, value=value, px=expires_in_ms
                )
                return
            # Redis 7.4 has field expiry commands but not HSETEX, so keep both operations atomic.
            await self._hash_set_with_expiry_script(keys=[hash_key], args=[key, value, expires_in_ms])
            return
        if keep_ttl:
            if redis_version >= _HASH_FIELD_EXPIRATION_COMMANDS_VERSION:
                await self._redis.hsetex(hash_key, key=key, value=value, keepttl=True)  # type: ignore[attr-defined]
            else:
                await self._hash_set_keep_ttl_script(keys=[hash_key], args=[key, value])
            return

        await self._redis.hset(hash_key, key, value)

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
        if await self._resolve_namespace_strategy() == "hash":
            await self._set_hash_value(key, value, expires_in, keep_ttl)
            return
        await self._redis.set(self._make_key(key), value, ex=expires_in, keepttl=keep_ttl)

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
        if await self._resolve_namespace_strategy() == "hash":
            hash_key = cast("str", self.namespace)
            if renew_for:
                redis_version = cast("tuple[int, int]", self._redis_version)
                script = (
                    self._hash_get_and_renew_with_hgetex_script
                    if redis_version >= _HASH_FIELD_EXPIRATION_COMMANDS_VERSION
                    else self._hash_get_and_renew_script
                )
                data = await script(keys=[hash_key], args=[key, self._expiry_milliseconds(renew_for)])
                return cast("bytes | None", data)
            return await self._redis.hget(hash_key, key)

        key = self._make_key(key)
        if renew_for:
            renew_for = self._expiry_seconds(renew_for)
            data = await self._get_and_renew_script(keys=[key], args=[renew_for])
            return cast("bytes | None", data)
        return await self._redis.get(key)

    async def delete(self, key: str) -> None:
        """Delete a value.

        If no such key exists, this is a no-op.

        Args:
            key: Key of the value to delete
        """
        if await self._resolve_namespace_strategy() == "hash":
            await self._redis.hdel(cast("str", self.namespace), key)
            return
        await self._redis.delete(self._make_key(key))

    async def delete_all(self) -> None:
        """Delete all stored values in the virtual key namespace.

        Raises:
            ImproperlyConfiguredException: If no namespace was configured
        """
        if not self.namespace:
            raise ImproperlyConfiguredException("Cannot perform delete operation: No namespace configured")

        if await self._resolve_namespace_strategy() == "hash":
            hash_key = self.namespace
            child_namespace = _escape_redis_glob(f"{self.namespace}_")
            await self._delete_hash_children_script(keys=[hash_key], args=[f"{child_namespace}*"])
            return
        await self._delete_all_script(keys=[], args=[f"{self.namespace}*:*"])

    async def exists(self, key: str) -> bool:
        """Check if a given ``key`` exists."""
        if await self._resolve_namespace_strategy() == "hash":
            return await self._redis.hexists(cast("str", self.namespace), key) == 1
        return await self._redis.exists(self._make_key(key)) == 1

    async def expires_in(self, key: str) -> int | None:
        """Get the time in seconds ``key`` expires in. If no such ``key`` exists or no
        expiry time was set, return ``None``.
        """
        if await self._resolve_namespace_strategy() == "hash":
            result = await self._redis.httl(cast("str", self.namespace), key)  # type: ignore[attr-defined]
            ttl = cast("list[int]", result)[0]
            return None if ttl == -2 else ttl
        ttl = await self._redis.ttl(self._make_key(key))
        return None if ttl == -2 else ttl
