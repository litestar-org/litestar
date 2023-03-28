from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

__all__ = ("ResponseCacheConfig", "default_cache_key_builder")


if TYPE_CHECKING:
    from starlite import Starlite
    from starlite.stores.base import Store
    from starlite.types import CacheKeyBuilder, Scope


def default_cache_key_builder(scope: Scope) -> str:
    """Given a request object, returns a cache key by combining the path with the sorted query params.

    Args:
        request: request used to generate cache key.

    Returns:
        A combination of url path and query parameters
    #
    """
    return scope["path"] + scope["query_string"].decode("latin-1")


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
    store: str = "request_cache"
    """Name of the :class:`Store <.stores.base.Store>` to use."""

    def get_store_from_app(self, app: Starlite) -> Store:
        """Get the store defined in :attr:`store` from an :class:`Starlite <.app.Starlite>` instance."""
        return app.stores.get(self.store)
