from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

from starlite.cache import Cache
from starlite.storage.memory import MemoryStorage

__all__ = (
    "CacheConfig",
    "default_cache_key_builder",
)


if TYPE_CHECKING:
    from starlite.connection import Request
    from starlite.storage.base import Storage
    from starlite.types import CacheKeyBuilder


def default_cache_key_builder(request: Request[Any, Any, Any]) -> str:
    """Given a request object, returns a cache key by combining the path with the sorted query params.

    Args:
        request (Request): request used to generate cache key.

    Returns:
        str: combination of url path and query parameters
    """
    query_params: list[tuple[str, Any]] = list(request.query_params.dict().items())
    query_params.sort(key=lambda x: x[0])
    return request.url.path + urlencode(query_params, doseq=True)


@dataclass
class CacheConfig:
    """Configuration for response caching.

    To enable response caching, pass an instance of this class to the :class:`Starlite <starlite.app.Starlite>` constructor
    using the 'cache_config' key.
    """

    backend: Storage | None = field(default=None)
    """Instance conforming to :class:`CacheBackendProtocol <starlite.cache.CacheBackendProtocol>`, default.

    :class:`MemoryStorage() <starlite.cache.MemoryStorage>`
    """
    expiration: int = field(default=60)
    """Default cache expiration in seconds."""
    cache_key_builder: CacheKeyBuilder = field(default=default_cache_key_builder)
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
