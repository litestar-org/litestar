from typing import TYPE_CHECKING, Any, List, Tuple
from urllib.parse import urlencode

from pydantic import BaseModel

from starlite.cache import Cache
from starlite.config.base_config import BaseConfigModel
from starlite.storage.base import Storage
from starlite.storage.memory import MemoryStorage
from starlite.types import CacheKeyBuilder

if TYPE_CHECKING:
    from starlite.connection import Request


def default_cache_key_builder(request: "Request[Any, Any, Any]") -> str:
    """Given a request object, returns a cache key by combining the path with the sorted query params.

    Args:
        request (Request): request used to generate cache key.

    Returns:
        str: combination of url path and query parameters
    """
    query_params: List[Tuple[str, Any]] = list(request.query_params.dict().items())
    query_params.sort(key=lambda x: x[0])
    return request.url.path + urlencode(query_params, doseq=True)


class CacheConfig(BaseModel):
    """Configuration for response caching.

    To enable response caching, pass an instance of this class to the :class:`Starlite <starlite.app.Starlite>` constructor
    using the 'cache_config' key.
    """

    class Config(BaseConfigModel):
        pass

    backend: Storage | None = None
    """Instance conforming to :class:`CacheBackendProtocol <starlite.cache.CacheBackendProtocol>`, default.

    :class:`MemoryStorage() <starlite.cache.MemoryStorage>`
    """
    expiration: int = 60
    """Default cache expiration in seconds."""
    cache_key_builder: CacheKeyBuilder = default_cache_key_builder
    """:class:`CacheKeyBuilder <starlite.types.CacheKeyBuilder>`,

    :func:`default_cache_key_builder <starlite.config.cache.default_cache_key_builder>` if not provided
    """

    def to_cache(self) -> Cache:
        """Create a cache wrapper from the config.

        Returns:
            An instance of :class:`Cache <starlite.cache.base.Cache>`
        """
        return Cache(
            backend=self.backend or MemoryStorage(),
            default_expiration=self.expiration,
            cache_key_builder=self.cache_key_builder,
        )
