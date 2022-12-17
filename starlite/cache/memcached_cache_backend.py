import pickle
from typing import Any, Callable, Optional

from pydantic import BaseModel

from starlite.exceptions import MissingDependencyException

try:
    from aiomcache import Client
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.memcached_cache_backend, install starlite with 'memcached' extra, e.g. `pip install starlite[memcached]`"
    ) from e


from starlite.cache.base import CacheBackendProtocol


class MemcachedCacheBackendConfig(BaseModel):
    """Memcached cache backend configuration."""

    host: str
    """Memcached host."""
    port: Optional[int] = None
    """memcached port (optional, defaults to 11211)"""
    pool_size: Optional[int] = None
    """Maximum number of memcached open connections (optional, defaults to 2)"""
    pool_minsize: Optional[int] = None
    """memcached minimum pool size (optional, by default set to `pool_size`)"""
    serialize: Callable[[Any], bytes] = pickle.dumps
    """A callable to serialize data that goes into the cache from an object to bytes, defaults to `pickle.dumps`"""
    deserialize: Callable[[bytes], Any] = pickle.loads
    """A callable to deserialize data coming from the cache from bytes to an object, defaults to `pickle.loads`"""


class MemcachedCacheBackend(CacheBackendProtocol):
    """Memcached-based cache backend."""

    _client: Client

    def __init__(self, config: MemcachedCacheBackendConfig) -> None:
        """Initialize `MemcachedCacheBackend`.

        Args:
            config: required configuration to connect to memcached.
        """
        self._config = config

    @property
    def _memcached_client(self) -> Client:
        if not hasattr(self, "_client"):
            self._client = Client(**self._config.dict(exclude_unset=True))

        return self._client

    async def get(self, key: str) -> Any:  # pylint: disable=invalid-overridden-method
        """Retrieve a value from cache corresponding to the given key.

        Args:
            key: name of cached value.

        Returns:
            Cached value if existing else `None`.
        """

        if value := await self._memcached_client.get(key=key.encode("utf-8")):
            return self._config.deserialize(value)
        return None

    async def set(self, key: str, value: Any, expiration: int) -> None:  # pylint: disable=invalid-overridden-method
        """Set sa value in cache for a given key for a duration determined by expiration.

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

        await self._memcached_client.set(  # pylint: disable=no-value-for-parameter
            key.encode(),
            self._config.serialize(value),
            exptime=expiration,
        )

    async def delete(self, key: str) -> None:  # pylint: disable=invalid-overridden-method
        """Delete a value from the cache and remove the given key.

        Args:
            key: key to be deleted from the cache.

        Notes:
            - return value is not used by Starlite internally.

        Returns:
            None
        """

        await self._memcached_client.delete(key=key.encode())  # pylint: disable=no-value-for-parameter
