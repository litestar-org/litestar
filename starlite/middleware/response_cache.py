from msgspec.msgpack import encode as encode_msgpack

from starlite.config.response_cache import ResponseCacheConfig
from starlite.enums import ScopeType
from starlite.types import ASGIApp, Message, Receive, Scope, Send
from starlite.utils import get_starlite_scope_state

from .base import AbstractMiddleware

__all__ = ["ResponseCacheMiddleware"]


class ResponseCacheMiddleware(AbstractMiddleware):
    def __init__(self, app: ASGIApp, config: ResponseCacheConfig) -> None:
        self.config = config
        super().__init__(app=app, scopes={ScopeType.HTTP})
        self._messages = []

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        route_handler = scope["route_handler"]
        if not getattr(route_handler, "cache", False):
            await self.app(scope, receive, send)
            return

        store = self.config.get_store_from_app(scope["app"])

        async def wrapped_send(message: Message) -> None:
            if not get_starlite_scope_state(scope, "is_cached"):
                self._messages.append(message)
                if message["type"] == "http.response.body" and not message["more_body"]:
                    key = (route_handler.cache_key_builder or self.config.key_builder)(scope)
                    await store.set(key, encode_msgpack(self._messages))
            await send(message)

        await self.app(scope, receive, wrapped_send)
