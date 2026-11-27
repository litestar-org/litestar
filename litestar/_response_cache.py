from inspect import isawaitable
from typing import TYPE_CHECKING, Any, TypeAlias, cast

from msgspec import DecodeError
from msgspec.msgpack import Decoder, encode

from litestar.enums import MediaType
from litestar.response import Redirect, Response
from litestar.utils.helpers import get_enum_string_value

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from litestar.background_tasks import BackgroundTask, BackgroundTasks
    from litestar.connection import Request
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.types import ASGIApp

__all__ = ("get_cached_response", "store_cache_entry", "to_cacheable_response")

CacheEntry: TypeAlias = tuple[int, str, str, dict[str, str], bytes]
"""Status code, media type, encoding, headers and body of a cached response."""

_cache_entry_decoder: Decoder[CacheEntry] = Decoder(CacheEntry)


def _cache_key(handler: "HTTPRouteHandler", request: "Request") -> str:
    return (handler.cache_key_builder or request.app.response_cache_config.key_builder)(request)


def _is_cacheable(handler: "HTTPRouteHandler", data: Any) -> bool:
    """Return whether the response for ``data`` can be cached."""
    from litestar.handlers.http_handlers.base import HTTPRouteHandler

    if handler.response_class is not Response or type(handler).to_response is not HTTPRouteHandler.to_response:
        return False
    if type(data) in (Response, Redirect):
        return not data.cookies and all(name.lower() != "set-cookie" for name in data.headers)
    return not isinstance(data, Response) and not callable(data)


def _create_cache_entry(
    handler: "HTTPRouteHandler", data: Any, request: "Request"
) -> "tuple[CacheEntry, BackgroundTask | BackgroundTasks | None]":
    """Render ``data`` into a cache entry and return it with the response's background task."""
    if return_dto_type := handler.return_dto:
        data = return_dto_type(request).data_to_encodable_type(data)

    response = data if isinstance(data, Response) else Response(data)
    default_media_type = MediaType.TEXT if isinstance(response, Redirect) else MediaType.JSON
    media_type = get_enum_string_value(response.media_type or handler.media_type or default_media_type)
    asgi_response = response.to_asgi_response(
        request=request, media_type=media_type, status_code=handler.status_code, type_encoders=handler.type_encoders
    )

    headers = {name: str(value) for name, value in response.headers.items()}
    if isinstance(response, Redirect):
        headers["location"] = asgi_response.headers["location"]

    cache_entry = (asgi_response.status_code, media_type, response.encoding, headers, asgi_response.body)
    return cache_entry, response.background


async def _cache_entry_to_response(
    handler: "HTTPRouteHandler",
    cache_entry: CacheEntry,
    request: "Request",
    background: "BackgroundTask | BackgroundTasks | None" = None,
) -> "ASGIApp":
    """Build the response for ``cache_entry`` through the handler's ``Response`` handler."""
    status_code, media_type, encoding, headers, body = cache_entry
    response = Response(
        body,
        status_code=status_code,
        media_type=media_type,
        encoding=encoding,
        headers=headers,
        background=background,
    )
    return await cast("Callable[..., Awaitable[ASGIApp]]", handler._response_type_handler)(
        data=response, request=request
    )


async def to_cacheable_response(
    handler: "HTTPRouteHandler", data: Any, request: "Request"
) -> "tuple[ASGIApp, CacheEntry | None]":
    """Build the response for ``data`` and, if it can be cached, its cache entry."""
    if isawaitable(data):
        data = await data

    if not _is_cacheable(handler, data):
        return await handler.to_response(data=data, request=request), None

    cache_entry, background = _create_cache_entry(handler, data, request)
    return await _cache_entry_to_response(handler, cache_entry, request, background), cache_entry


async def get_cached_response(handler: "HTTPRouteHandler", request: "Request") -> "ASGIApp | None":
    """Build the response from the cache entry stored for ``request``, if a valid one exists."""
    store = request.app.response_cache_config.get_store_from_app(request.app)
    if not (cached := await store.get(_cache_key(handler, request))):
        return None

    try:
        cache_entry = _cache_entry_decoder.decode(cached)
    except DecodeError:
        return None
    return await _cache_entry_to_response(handler, cache_entry, request)


async def store_cache_entry(handler: "HTTPRouteHandler", request: "Request", cache_entry: CacheEntry) -> None:
    """Store ``cache_entry`` for ``request`` if the ``cache_response_filter`` accepts its status code."""
    cache_config = request.app.response_cache_config
    if not cache_config.cache_response_filter(request.scope, cache_entry[0]):
        return

    cache = handler.cache
    await cache_config.get_store_from_app(request.app).set(
        _cache_key(handler, request),
        encode(cache_entry),
        expires_in=cache_config.default_expiration if cache is True else cache if isinstance(cache, int) else None,
    )
