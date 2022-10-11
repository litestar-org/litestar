import pickle
from typing import Any, Optional

from pydantic import BaseModel

from starlite.exceptions import MissingDependencyException

try:
    from aiomcache import Client
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.memcached_cahce_backend, install starlite with 'memcached_cahce_backend' extra, e.g. `pip install starlite[memcached_cahce_backend]`"
    ) from e


from starlite.cache.base import CacheBackendProtocol


class MemcachedCacheBackendConfig(BaseModel):
    """Memcached cache backend configuration."""

    host: str
    """memcached host"""
    port: Optional[int] = None
    """memcached port (optional, defaults to 11211)"""
    pool_size: Optional[int] = None
    """Maximum number of memcached open connections (optional, defaults to 2)"""
    pool_minsize: Optional[str] = None
    """memcached minimum pool size (optional, by default equals to `pool_size`)"""


class MemcachedCacheBackend(CacheBackendProtocol):
    def __init__(self, config: MemcachedCacheBackendConfig):
        """This class offers a cache backend based on memcached.

        Args:
            config: required configuration to connect to memcached.
        """
        self._config = config
        self._client: Client = None

    @property
    def _memcached_client(self) -> Client:
        if not self._client:
            self._client = Client(**self._config.dict(exclude_unset=True))

        return self._client

    async def get(self, key: str) -> Any:  # pylint: disable=invalid-overridden-method
        """Retrieves a value from cache corresponding to the given key.

        Args:
            key: name of cached value.

        Returns:
            Cached value if existing else `None`.
        """

        value = await self._memcached_client.get(key=key.encode())
        return pickle.loads(value)

    async def set(self, key: str, value: Any, expiration: int) -> None:  # pylint: disable=invalid-overridden-method
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
            None
        """

        await self._memcached_client.set(key.encode(), pickle.dumps(value), exptime=expiration)
        return None

    async def delete(self, key: str) -> None:  # pylint: disable=invalid-overridden-method
        """Deletes a value from the cache and removes the given key.

        Args:
            key: key to be deleted from the cache.

        Notes:
            - return value is not used by Starlite internally.

        Returns:
            None
        """

        await self._memcached_client.delete(key=key.encode())
        return None
