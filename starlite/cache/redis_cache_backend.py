from typing import Any, Optional

from pydantic import BaseModel

from starlite import MissingDependencyException

try:
    from redis.asyncio import Redis
    from redis.asyncio.connection import ConnectionPool
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.redis_cache_backend, install starlite with 'redis_cache_backend' extra, e.g. `pip install starlite[redis_cache_backend]`"
    ) from e


from starlite.cache.base import CacheBackendProtocol


class RedisCacheBackendConfig(BaseModel):
    url: str
    db: Optional[int] = None
    port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None


class RedisCacheBackend(CacheBackendProtocol):
    def __init__(self, config: RedisCacheBackendConfig):
        self._config = config
        self._redis_int: Redis = None  # type: ignore[assignment]

    @property
    def _redis(self) -> Redis:
        if not self._redis_int:
            pool = ConnectionPool.from_url(**self._config.dict(exclude_unset=True))
            self._redis_int = Redis(connection_pool=pool)

        return self._redis_int

    async def get(self, key: str) -> Any:  # pylint: disable=invalid-overridden-method
        """Retrieves a value from cache corresponding to the given key.

        Args:
            key: name of cached value.

        Returns:
            Cached value if existing else `None`.
        """

        value = await self._redis.get(key)
        return value

    async def set(self, key: str, value: Any, expiration: int) -> Any:  # pylint: disable=invalid-overridden-method
        """Set sa value in cache for a given key for a duration determined by
        expiration.

        Args:
            key: key to cache `value` under.
            value: the value to be cached.
            expiration: expiration of cached value in seconds.

        Notes:
            - expiration is in seconds.
            - return value is not used by Starlite internally.

        Returns:
            Any
        """

        await self._redis.set(key, value, ex=expiration)
        return None

    async def delete(self, key: str) -> Any:  # pylint: disable=invalid-overridden-method
        """Deletes a value from the cache and removes the given key.

        Args:
            key: key to be deleted from the cache.

        Notes:
            - return value is not used by Starlite internally.

        Returns:
            Any
        """

        await self._redis.delete(key)
        return None
