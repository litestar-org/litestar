from typing import TYPE_CHECKING, cast

from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from starlite.connection import Request
from starlite.enums import ScopeType
from starlite.exceptions.utils import create_exception_response
from starlite.middleware.base import MiddlewareProtocol
from starlite.utils.exception import get_exception_handler

if TYPE_CHECKING:

    from starlette.responses import Response as StarletteResponse

    from starlite.app import Starlite
    from starlite.types import ASGIApp, ExceptionHandlersMap, Receive, Scope, Send


class ExceptionHandlerMiddleware(MiddlewareProtocol):
    def __init__(self, app: "ASGIApp", debug: bool, exception_handlers: "ExceptionHandlersMap"):
        """This middleware is used to wrap an ASGIApp inside a try catch block
        and handles any exceptions raised.

        Notes:
            * It's used in multiple layers of Starlite.

        Args:
            app: The 'next' ASGI app to call.
            debug: Whether 'debug' mode is enabled
            exception_handlers: A dictionary mapping status codes and/or exception types to handler functions.
        """
        self.app = app
        self.exception_handlers = exception_handlers
        self.debug = debug

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:  # pragma: no cover
        try:
            await self.app(scope, receive, send)
        except Exception as exc:  # pylint: disable=broad-except
            starlite_app = cast("Starlite", scope["app"])
            for hook in starlite_app.after_exception:
                await hook(exc, scope, starlite_app.state)

            if scope["type"] == ScopeType.HTTP:
                exception_handler = (
                    get_exception_handler(self.exception_handlers, exc) or self.default_http_exception_handler
                )
                response = exception_handler(Request(scope=scope, receive=receive, send=send), exc)
                await response(scope=scope, receive=receive, send=send)
            else:
                status_code = (
                    exc.status_code if isinstance(exc, StarletteHTTPException) else HTTP_500_INTERNAL_SERVER_ERROR
                )
                # The 4000+ code range for websockets is customizable, hence we simply add it to the http status code
                status_code += 4000
                reason = repr(exc)
                await send({"type": "websocket.close", "code": status_code, "reason": reason})

    def default_http_exception_handler(self, request: Request, exc: Exception) -> "StarletteResponse":
        """Default handler for exceptions subclassed from HTTPException."""
        status_code = exc.status_code if isinstance(exc, StarletteHTTPException) else HTTP_500_INTERNAL_SERVER_ERROR
        if status_code == HTTP_500_INTERNAL_SERVER_ERROR and self.debug:
            # in debug mode, we just use the serve_middleware to create an HTML formatted response for us
            server_middleware = ServerErrorMiddleware(app=self)
            return server_middleware.debug_response(request=request, exc=exc)
        return create_exception_response(exc)
