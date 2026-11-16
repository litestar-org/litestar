from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeAlias

from msgspec import DecodeError
from msgspec.msgpack import Decoder, encode

from litestar.enums import MediaType
from litestar.response import Redirect, Response
from litestar.utils.helpers import get_enum_string_value

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

CacheEntry: TypeAlias = tuple[int, str, str, list[tuple[str, str]], bytes]
"""Status code, media type, encoding, headers and body of a cached response."""

_KEY_SUFFIX = "::body"
_cache_entry_decoder: Decoder[CacheEntry] = Decoder(CacheEntry)


def _cache_key(handler: HTTPRouteHandler, request: Request) -> str:
    return (handler.cache_key_builder or request.app.response_cache_config.key_builder)(request) + _KEY_SUFFIX


def is_cacheable(handler: HTTPRouteHandler, data: Any) -> bool:
    """Return whether the response for ``data`` can be cached.

    Only plain return values, :class:`Response <litestar.response.Response>` and
    :class:`Redirect <litestar.response.Redirect>` instances without cookies are cached, and only when the handler uses
    the default ``response_class``.

    Args:
        handler: The route handler that returned ``data``
        data: The value returned by the route handler function

    Returns:
        Whether the response for ``data`` can be cached.
    """
    if handler.response_class is not Response:
        return False
    if type(data) in (Response, Redirect):
        return not data.cookies and all(name.lower() != "set-cookie" for name in data.headers)
    return not isinstance(data, Response) and not callable(data)


def create_cache_entry(
    handler: HTTPRouteHandler, data: Any, request: Request
) -> tuple[CacheEntry, BackgroundTask | BackgroundTasks | None]:
    """Render ``data`` into a :data:`CacheEntry`, without layered headers, cookies, background tasks or ``after_request``.

    Args:
        handler: The route handler that returned ``data``
        data: The value returned by the route handler function
        request: The :class:`Request <litestar.connection.Request>` instance

    Returns:
        The cache entry and the background task of the returned response.
    """
    if return_dto_type := handler.return_dto:
        data = return_dto_type(request).data_to_encodable_type(data)

    response = (
        data
        if isinstance(data, Response)
        else Response(data, media_type=handler.media_type, status_code=handler.status_code)
    )
    default_media_type = MediaType.TEXT if isinstance(response, Redirect) else MediaType.JSON
    media_type = get_enum_string_value(response.media_type or handler.media_type or default_media_type)
    asgi_response = response.to_asgi_response(
        request=request, media_type=media_type, status_code=handler.status_code, type_encoders=handler.type_encoders
    )

    headers = [(name, str(value)) for name, value in response.headers.items() if name.lower() != "content-length"]
    if isinstance(response, Redirect):
        headers.append(("location", asgi_response.headers["location"]))

    cache_entry = (asgi_response.status_code, media_type, response.encoding, headers, asgi_response.body)
    return cache_entry, response.background


def cache_entry_to_response(
    cache_entry: CacheEntry, background: BackgroundTask | BackgroundTasks | None = None
) -> Response:
    """Build a :class:`Response <litestar.response.Response>` from a :data:`CacheEntry`.

    Args:
        cache_entry: The cache entry
        background: The background task of the response the entry was created from, run on a cache miss only

    Returns:
        A response with the cached status code, media type, encoding, headers and body.
    """
    status_code, media_type, encoding, headers, body = cache_entry
    return Response(
        body,
        status_code=status_code,
        media_type=media_type,
        encoding=encoding,
        headers=dict(headers),
        background=background,
    )


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
