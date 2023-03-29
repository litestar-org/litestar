from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any
from urllib.parse import urlencode

__all__ = ("ResponseCacheConfig", "default_cache_key_builder")


if TYPE_CHECKING:
    from starlite import Starlite
    from starlite.connection import Request
    from starlite.stores.base import Store
    from starlite.types import CacheKeyBuilder


def default_cache_key_builder(request: Request[Any, Any, Any]) -> str:
    """Given a request object, returns a cache key by combining the path with the sorted query params.

    Args:
        request: request used to generate cache key.

    Returns:
        A combination of url path and query parameters
    """
    query_params: list[tuple[str, Any]] = list(request.query_params.dict().items())
    query_params.sort(key=lambda x: x[0])
    return request.url.path + urlencode(query_params, doseq=True)


@dataclass
class ResponseCacheConfig:
    """Configuration for response caching.

    To enable response caching, pass an instance of this class to :class:`Starlite <.app.Starlite>` using the
    ``response_cache_config`` key.
    """

    default_expiration: int = field(default=60)
    """Default cache expiration in seconds."""
    key_builder: CacheKeyBuilder = field(default=default_cache_key_builder)
    """:class:`CacheKeyBuilder <.types.CacheKeyBuilder>`. Defaults to :func:`default_cache_key_builder`."""
    store: str = "response_cache"
    """Name of the :class:`Store <.stores.base.Store>` to use."""

    def get_store_from_app(self, app: Starlite) -> Store:
        """Get the store defined in :attr:`store` from an :class:`Starlite <.app.Starlite>` instance."""
        return app.stores.get(self.store)
