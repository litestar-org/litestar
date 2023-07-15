from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, final
from urllib.parse import urlencode

__all__ = ("ResponseCacheConfig", "default_cache_key_builder", "CACHE_FOREVER")


if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.connection import Request
    from litestar.stores.base import Store
    from litestar.types import CacheKeyBuilder


@final
class CACHE_FOREVER:  # noqa: N801
    """Sentinel value indicating that a cached response should be stored without an expiration, explicitly skipping the
    default expiration
    """


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

    To enable response caching, pass an instance of this class to :class:`Litestar <.app.Litestar>` using the
    ``response_cache_config`` key.
    """

    default_expiration: int | None = 60
    """Default cache expiration in seconds used when a route handler is configured with ``cache=True``."""
    key_builder: CacheKeyBuilder = field(default=default_cache_key_builder)
    """:class:`CacheKeyBuilder <.types.CacheKeyBuilder>`. Defaults to :func:`default_cache_key_builder`."""
    store: str = "response_cache"
    """Name of the :class:`Store <.stores.base.Store>` to use."""

    def get_store_from_app(self, app: Litestar) -> Store:
        """Get the store defined in :attr:`store` from an :class:`Litestar <.app.Litestar>` instance."""
        return app.stores.get(self.store)
