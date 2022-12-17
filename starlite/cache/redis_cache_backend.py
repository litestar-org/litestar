from typing import Any, Optional

from pydantic import BaseModel

from starlite.exceptions import MissingDependencyException

try:
    from redis.asyncio import Redis
    from redis.asyncio.connection import ConnectionPool
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.redis_cache_backend, install starlite with 'redis' extra, e.g. `pip install starlite[redis]`"
    ) from e


from starlite.cache.base import CacheBackendProtocol


class RedisCacheBackendConfig(BaseModel):
    """Redis cache backend configuration."""

    url: str
    """Redis connection URL."""
    db: Optional[int] = None
    """Redis DB ID (optional)"""
    port: Optional[int] = None
    """Redis port (optional)"""
    username: Optional[str] = None
    """A username to use when connecting to Redis (optional)"""
    password: Optional[str] = None
    """A password to use when connecting to Redis (optional)"""


class RedisCacheBackend(CacheBackendProtocol):
    """Redis-based cache backend."""

    def __init__(self, config: RedisCacheBackendConfig):
        """Initialize `RedisCacheBackend`

        Args:
            config: required configuration to connect to Redis.
        """
        self._config = config
        self._redis_int: Redis = None  # type: ignore[assignment]

    @property
    def _redis(self) -> Redis:
        if not self._redis_int:
            pool = ConnectionPool.from_url(**self._config.dict(exclude_unset=True))
            self._redis_int = Redis(connection_pool=pool)

        return self._redis_int

    async def get(self, key: str) -> Any:  # pylint: disable=invalid-overridden-method
        """Retrieve a value from cache corresponding to the given key.

        Args:
            key: name of cached value.

        Returns:
            Cached value if existing else `None`.
        """

        return await self._redis.get(key)

    async def set(self, key: str, value: Any, expiration: int) -> None:  # pylint: disable=invalid-overridden-method
        """Set a value in cache for a given key for a duration determined by expiration.

        Args:
            key: key to cache `value` under.
            value: the value to be cached.
            expiration: expiration of cached value in seconds.

        Notes:
            - expiration is in seconds.
            - return value is not used by Starlite internally.

        Returns:
            None
        """

        await self._redis.set(key, value, ex=expiration)

    async def delete(self, key: str) -> None:  # pylint: disable=invalid-overridden-method
        """Delete a value from the cache and removes the given key.

        Args:
            key: key to be deleted from the cache.

        Notes:
            - return value is not used by Starlite internally.

        Returns:
            None
        """

        await self._redis.delete(key)
