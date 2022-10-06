from typing import Any, Optional

from pydantic import BaseModel

from starlite import MissingDependencyException

try:
    import aioredis
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.redis_cache_backend, install starlite with 'redis_cache_backend' extra, e.g. `pip install starlite[redis_cache_backend]`"
    ) from e


from starlite.cache.base import CacheBackendProtocol


class RedisCacheBackendConfig(BaseModel):
    connection_string: str
    db: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None

    def to_kwargs(self) -> dict:
        kwargs = super().dict()
        kwargs.pop("connection_string")
        return kwargs


class RedisCacheBackend(CacheBackendProtocol):
    def __init__(self, config: RedisCacheBackendConfig):
        self._config = config
        self._redis = None

    @property
    def _get_redis(self):
        if not self._redis:
            self._redis = aioredis.from_url(self._config.connection_string, **self._config.to_kwargs())

        return self._redis

    async def get(self, key: str) -> Any:
        """Retrieves a value from cache corresponding to the given key.

        Args:
            key: name of cached value.

        Returns:
            Cached value if existing else `None`.
        """

        value = await self._get_redis.get(key)
        return value

    async def set(self, key: str, value: Any, expiration: int) -> Any:
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

        await self._get_redis.set(key, value, ex=expiration)
        return None

    async def delete(self, key: str) -> Any:
        """Deletes a value from the cache and removes the given key.

        Args:
            key: key to be deleted from the cache.

        Notes:
            - return value is not used by Starlite internally.

        Returns:
            Any
        """

        await self._get_redis.delete(key)
