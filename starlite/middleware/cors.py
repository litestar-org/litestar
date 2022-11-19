from typing import TYPE_CHECKING

from starlite.datastructures import Headers, MutableScopeHeaders
from starlite.enums import ScopeType
from starlite.middleware.base import AbstractMiddleware

if TYPE_CHECKING:
    from starlite.config.cors import CORSConfig
    from starlite.types import ASGIApp, Message, Receive, Scope, Send


class CORSMiddleware(AbstractMiddleware):
    """CORS Middleware."""

    __slots__ = ("config",)

    def __init__(self, app: "ASGIApp", config: "CORSConfig"):
        """Middleware that adds CORS validation to the application.

        Args:
            app: The 'next' ASGI app to call.
            config: An instance of [CORSConfig][starlite.config.cors.CORSConfig]
        """
        super().__init__(app=app, scopes={ScopeType.HTTP})
        self.config = config

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        headers = Headers.from_scope(scope=scope)

        origin = headers.get("origin")

        if not origin:
            await self.app(scope, receive, send)
        else:
            await self.app(scope, receive, self.send_wrapper(send=send, origin=origin, has_cookie="cookie" in headers))

    def send_wrapper(self, send: "Send", origin: str, has_cookie: bool) -> "Send":
        """Wrap `send` to ensure that state is not disconnected.

        Args:
            has_cookie: Boolean flag dictating if the connection has a cookie set.
            origin: The value of the 'Origin' header.
            send: The ASGI send function.

        Returns:
            An ASGI send function.
        """

        async def wrapped_send(message: "Message") -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                headers = MutableScopeHeaders.from_message(message=message)
                headers.update(self.config.simple_headers)

                if (self.config.is_allow_all_origins and has_cookie) or (
                    not self.config.is_allow_all_origins and self.config.is_origin_allowed(origin=origin)
                ):

                    headers["Access-Control-Allow-Origin"] = origin
                    headers["Vary"] = "Origin"

            await send(message)

        return wrapped_send
