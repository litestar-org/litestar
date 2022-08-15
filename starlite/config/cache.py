from typing import TYPE_CHECKING, Any, List, Tuple
from urllib.parse import urlencode

from pydantic import BaseConfig, BaseModel

from starlite.cache import CacheBackendProtocol, SimpleCacheBackend
from starlite.types import CacheKeyBuilder

if TYPE_CHECKING:
    from starlite.connection import Request


def default_cache_key_builder(request: "Request") -> str:
    """Given a request object, returns a cache key by combining the path with
    the sorted query params.

    Args:
        request (Request): request used to generate cache key.

    Returns:
        str: combination of url path and query parameters
    """
    query_params: List[Tuple[str, Any]] = list(request.query_params.items())
    query_params.sort(key=lambda x: x[0])
    return request.url.path + urlencode(query_params, doseq=True)


class CacheConfig(BaseModel):
    """Configuration for response caching.

    To enable response caching, pass an instance of this class to the
    [Starlite][starlite.app.Starlite] constructor using the
    'cache_config' key.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True

    backend: CacheBackendProtocol = SimpleCacheBackend()
    """
        Instance conforming to [CacheBackendProtocol][starlite.cache.CacheBackendProtocol], default
        [SimpleCacheBackend()][starlite.cache.SimpleCacheBackend]
    """
    expiration: int = 60  # value in seconds
    """
        Default cache expiration in seconds
    """
    cache_key_builder: CacheKeyBuilder = default_cache_key_builder
    """
        [CacheKeyBuilder][starlite.types.CacheKeyBuilder],
        [default_cache_key_builder][starlite.config.cache.default_cache_key_builder] if not provided
    """
