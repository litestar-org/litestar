from __future__ import annotations

from typing import TYPE_CHECKING, cast

from msgspec.msgpack import encode as encode_msgpack

from litestar import Request
from litestar.config.response_cache import default_cache_key_builder, default_do_cache_predicate
from litestar.constants import HTTP_RESPONSE_BODY, HTTP_RESPONSE_START
from litestar.enums import ScopeType
from litestar.middleware.base import ASGIMiddleware
from litestar.utils.empty import value_or_default
from litestar.utils.scope.state import ScopeState

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.handlers import HTTPRouteHandler
    from litestar.types import ASGIApp, CacheKeyBuilder, HTTPScope, Message, Receive, Scope, Send

__all__ = ["ResponseCacheMiddleware"]


class ResponseCacheMiddleware(ASGIMiddleware):
    """Response cache middleware."""

    scopes = (ScopeType.HTTP,)

    def __init__(
        self,
        *,
        default_expiration: int | None = 60,
        key_builder: CacheKeyBuilder = default_cache_key_builder,
        store: str = "response_cache",
        cache_response_filter: Callable[[HTTPScope, int], bool] = default_do_cache_predicate,
    ) -> None:
        """Middleware that caches responses of route handlers configured with ``cache``.

        Args:
            default_expiration: Default cache expiration in seconds used when a route handler is
                configured with ``cache=True``.
            key_builder: :class:`CacheKeyBuilder <.types.CacheKeyBuilder>` used unless the route
                handler defines its own.
            store: Name of the :class:`Store <.stores.base.Store>` to cache responses in.
            cache_response_filter: A callable that receives the connection scope and a status code,
                and returns a boolean indicating whether the response should be cached.
        """
        self.default_expiration = default_expiration
        self.key_builder = key_builder
        self.store = store
        self.cache_response_filter = cache_response_filter

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        """Handle ASGI call.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
            next_app: The next ASGI application in the middleware stack to call.

        Returns:
            None
        """
        route_handler = cast("HTTPRouteHandler", scope["route_handler"])

        if not route_handler.cache:
            await next_app(scope, receive, send)
            return

        expires_in: int | None = None
        if route_handler.cache is True:
            expires_in = self.default_expiration
        elif route_handler.cache is not False and isinstance(route_handler.cache, int):
            expires_in = route_handler.cache

        connection_state = ScopeState.from_scope(scope)

        messages: list[Message] = []

        async def wrapped_send(message: Message) -> None:
            if not value_or_default(connection_state.is_cached, False):
                if message["type"] == HTTP_RESPONSE_START:
                    do_cache = connection_state.do_cache = self.cache_response_filter(
                        cast("HTTPScope", scope), message["status"]
                    )
                    if do_cache:
                        messages.append(message)
                elif value_or_default(connection_state.do_cache, False):
                    messages.append(message)

                if messages and message["type"] == HTTP_RESPONSE_BODY and not message.get("more_body"):
                    key = (route_handler.cache_key_builder or self.key_builder)(Request(scope))
                    store = scope["litestar_app"].stores.get(self.store)
                    await store.set(key, encode_msgpack(messages), expires_in=expires_in)
            await send(message)

        await next_app(scope, receive, wrapped_send)
