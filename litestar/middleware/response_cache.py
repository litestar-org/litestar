from __future__ import annotations

from msgspec.msgpack import encode as encode_msgpack

from litestar.enums import ScopeType
from litestar.utils import get_litestar_scope_state

from .base import AbstractMiddleware

__all__ = ["ResponseCacheMiddleware"]

from typing import TYPE_CHECKING, cast

from litestar import Request
from litestar.constants import SCOPE_STATE_IS_CACHED

if TYPE_CHECKING:
    from litestar.config.response_cache import ResponseCacheConfig
    from litestar.handlers import HTTPRouteHandler
    from litestar.types import ASGIApp, Message, Receive, Scope, Send


class ResponseCacheMiddleware(AbstractMiddleware):
    def __init__(self, app: ASGIApp, config: ResponseCacheConfig) -> None:
        self.config = config
        super().__init__(app=app, scopes={ScopeType.HTTP})

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        route_handler = cast("HTTPRouteHandler", scope["route_handler"])
        store = self.config.get_store_from_app(scope["app"])

        expires_in: int | None = None
        if route_handler.cache is True:
            expires_in = self.config.default_expiration
        elif route_handler.cache is not False and isinstance(route_handler.cache, int):
            expires_in = route_handler.cache

        messages = []

        async def wrapped_send(message: Message) -> None:
            if not get_litestar_scope_state(scope, SCOPE_STATE_IS_CACHED):
                messages.append(message)
                if message["type"] == "http.response.body" and not message["more_body"]:
                    key = (route_handler.cache_key_builder or self.config.key_builder)(Request(scope))
                    await store.set(key, encode_msgpack(messages), expires_in=expires_in)
            await send(message)

        await self.app(scope, receive, wrapped_send)
