from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

from msgspec import DecodeError
from msgspec.msgpack import Decoder, encode

from litestar.handlers.http_handlers._utils import normalize_headers
from litestar.response import File, Response, Stream, Template
from litestar.response.base import ASGIResponse
from litestar.response.streaming import ASGIStreamingResponse

if TYPE_CHECKING:
    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.handlers.http_handlers import HTTPRouteHandler

__all__ = (
    "CacheEntry",
    "cache_entry_to_response",
    "create_cache_entry",
    "get_cache_entry",
    "is_cacheable",
    "store_cache_entry",
)

CacheEntry: TypeAlias = tuple[int, list[tuple[str, str]], bytes]
"""Status code, headers and body of a cached response."""

_KEY_SUFFIX = "::body"
_EXCLUDED_HEADERS = frozenset((b"content-length", b"set-cookie"))
_cache_entry_decoder: Decoder[CacheEntry] = Decoder(CacheEntry)


def _cache_key(handler: HTTPRouteHandler, request: Request) -> str:
    return (handler.cache_key_builder or request.app.response_cache_config.key_builder)(request) + _KEY_SUFFIX


def is_cacheable(data: Any) -> bool:
    """Return whether the response for ``data`` can be cached.

    Streamed responses, templates, responses with their own cookies and ASGI applications are not cached.

    Args:
        data: The value returned by the route handler function

    Returns:
        Whether the response for ``data`` can be cached.
    """
    if isinstance(data, (Stream, File, Template)):
        return False
    if isinstance(data, Response):
        return not data.cookies
    return not callable(data)


def create_cache_entry(
    handler: HTTPRouteHandler, data: Any, request: Request
) -> tuple[CacheEntry, BackgroundTask | BackgroundTasks | None] | None:
    """Render ``data`` into a :data:`CacheEntry`, without cookies, background tasks or ``after_request``.

    Args:
        handler: The route handler that returned ``data``
        data: The value returned by the route handler function
        request: The :class:`Request <litestar.connection.Request>` instance

    Returns:
        The cache entry and the background task of the returned response, or ``None`` if the rendered response
        cannot be cached.
    """
    if return_dto_type := handler.return_dto:
        data = return_dto_type(request).data_to_encodable_type(data)

    response = (
        data
        if isinstance(data, Response)
        else handler.response_class(
            content=data,
            media_type=handler.media_type,
            status_code=handler.status_code,
            type_encoders=handler.type_encoders,
        )
    )
    background, response.background = response.background, None
    layered_headers = normalize_headers(handler.response_headers)
    asgi_response = response.to_asgi_response(
        request=request,
        headers=layered_headers,
        media_type=handler.media_type,
        status_code=handler.status_code,
        type_encoders=handler.type_encoders,
    )
    if not isinstance(asgi_response, ASGIResponse) or isinstance(asgi_response, ASGIStreamingResponse):
        response.background = background
        return None

    excluded = _EXCLUDED_HEADERS | {name.lower().encode("latin-1") for name in layered_headers}
    headers = [
        (name.decode("latin-1"), value.decode("latin-1"))
        for name, value in asgi_response.headers.headers
        if name.lower() not in excluded
    ]
    return (asgi_response.status_code, headers, asgi_response.body), background


def cache_entry_to_response(
    cache_entry: CacheEntry, background: BackgroundTask | BackgroundTasks | None = None
) -> Response:
    """Build a :class:`Response <litestar.response.Response>` from a :data:`CacheEntry`.

    Args:
        cache_entry: The cache entry
        background: The background task of the response the entry was created from, run on a cache miss only

    Returns:
        A response with the cached status code, headers and body.
    """
    status_code, headers, body = cache_entry
    return Response(body, status_code=status_code, headers=dict(headers), background=background)


async def get_cache_entry(handler: HTTPRouteHandler, request: Request) -> CacheEntry | None:
    """Return the cache entry stored for ``request``, if existing.

    Args:
        handler: The route handler for ``request``
        request: The :class:`Request <litestar.connection.Request>` instance

    Returns:
        The cache entry, or ``None`` if there is none or it cannot be decoded.
    """
    store = request.app.response_cache_config.get_store_from_app(request.app)
    if not (cached := await store.get(_cache_key(handler, request))):
        return None

    try:
        return _cache_entry_decoder.decode(cached)
    except DecodeError:
        return None


async def store_cache_entry(handler: HTTPRouteHandler, request: Request, cache_entry: CacheEntry) -> None:
    """Store ``cache_entry`` for ``request`` if the configured ``cache_response_filter`` accepts its status code.

    Args:
        handler: The route handler for ``request``
        request: The :class:`Request <litestar.connection.Request>` instance
        cache_entry: The cache entry to store
    """
    cache_config = request.app.response_cache_config
    if not cache_config.cache_response_filter(request.scope, cache_entry[0]):
        return

    expires_in: int | None
    if handler.cache is True:
        expires_in = cache_config.default_expiration
    elif isinstance(handler.cache, int):
        expires_in = handler.cache
    else:
        expires_in = None

    await cache_config.get_store_from_app(request.app).set(
        _cache_key(handler, request), encode(cache_entry), expires_in=expires_in
    )
