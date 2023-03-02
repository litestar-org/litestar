from __future__ import annotations

from dataclasses import asdict, dataclass, field
from inspect import getmro
from typing import TYPE_CHECKING, Any, Type, cast

from starlite import Response
from starlite.connection import Request
from starlite.datastructures import Headers
from starlite.enums import ScopeType
from starlite.exceptions import WebSocketException
from starlite.middleware.cors import CORSMiddleware
from starlite.middleware.exceptions.debug_response import create_debug_response
from starlite.status_codes import HTTP_500_INTERNAL_SERVER_ERROR

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.types import (
        ASGIApp,
        ExceptionHandler,
        ExceptionHandlersMap,
        Receive,
        Scope,
        Send,
    )
    from starlite.types.asgi_types import WebSocketCloseEvent


def get_exception_handler(exception_handlers: ExceptionHandlersMap, exc: Exception) -> ExceptionHandler | None:
    """Given a dictionary that maps exceptions and status codes to handler functions, and an exception, returns the
    appropriate handler if existing.

    Status codes are given preference over exception type.

    If no status code match exists, each class in the MRO of the exception type is checked and
    the first matching handler is returned.

    Finally, if a ``500`` handler is registered, it will be returned for any exception that isn't a
    subclass of :class:`HTTPException <starlite.exceptions.HTTPException>`.

    Args:
        exception_handlers: Mapping of status codes and exception types to handlers.
        exc: Exception Instance to be resolved to a handler.

    Returns:
        Optional exception handler callable.
    """
    if not exception_handlers:
        return None
    status_code: int | None = getattr(exc, "status_code", None)
    if status_code and (exception_handler := exception_handlers.get(status_code)):
        return exception_handler
    for cls in getmro(type(exc)):
        if cls in exception_handlers:
            return exception_handlers[cast("Type[Exception]", cls)]
    if not hasattr(exc, "status_code") and HTTP_500_INTERNAL_SERVER_ERROR in exception_handlers:
        return exception_handlers[HTTP_500_INTERNAL_SERVER_ERROR]
    return None


@dataclass
class ExceptionResponseContent:
    """Represent the contents of an exception-response."""

    status_code: int
    """Exception status code."""
    detail: str
    """Exception details or message."""
    headers: dict[str, str] | None = field(default=None)
    """Headers to attach to the response."""
    extra: dict[str, Any] | list[Any] | None = field(default=None)
    """An extra mapping to attach to the exception."""

    def to_response(self) -> Response:
        """Create a response from the model attributes.

        Returns:
            A response instance.
        """
        from starlite.response import Response

        return Response(
            content={k: v for k, v in asdict(self).items() if k != "headers" and v is not None},
            headers=self.headers,
            status_code=self.status_code,
        )


def create_exception_response(exc: Exception) -> Response:
    """Construct a response from an exception.

    Notes:
        - For instances of :class:`HTTPException <starlite.exceptions.HTTPException>` or other exception classes that have a
          ``status_code`` attribute (e.g. Starlette exceptions), the status code is drawn from the exception, otherwise
          response status is ``HTTP_500_INTERNAL_SERVER_ERROR``.

    Args:
        exc: An exception.

    Returns:
        Response: HTTP response constructed from exception details.
    """
    content = ExceptionResponseContent(
        status_code=getattr(exc, "status_code", HTTP_500_INTERNAL_SERVER_ERROR),
        detail=getattr(exc, "detail", repr(exc)),
        headers=getattr(exc, "headers", None),
        extra=getattr(exc, "extra", None),
    )
    return content.to_response()


class ExceptionHandlerMiddleware:
    """Middleware used to wrap an ASGIApp inside a try catch block and handle any exceptions raised.

    This used in multiple layers of Starlite.
    """

    def __init__(self, app: ASGIApp, debug: bool, exception_handlers: ExceptionHandlersMap) -> None:
        """Initialize ``ExceptionHandlerMiddleware``.

        Args:
            app: The ``next`` ASGI app to call.
            debug: Whether ``debug`` mode is enabled
            exception_handlers: A dictionary mapping status codes and/or exception types to handler functions.
        """
        self.app = app
        self.exception_handlers = exception_handlers
        self.debug = debug

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI-callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        try:
            await self.app(scope, receive, send)
        except Exception as e:  # pylint: disable=broad-except
            starlite_app = scope["app"]
            if self.debug and starlite_app.logger:
                starlite_app.logger.debug(
                    "exception raised on %s connection request to route %s", scope["type"], scope["path"], exc_info=True
                )

            for hook in starlite_app.after_exception:
                await hook(e, scope, starlite_app.state)

            if scope["type"] == ScopeType.HTTP:
                await self.handle_request_exception(
                    starlite_app=starlite_app, scope=scope, receive=receive, send=send, exc=e
                )
            else:
                await self.handle_websocket_exception(send=send, exc=e)

    async def handle_request_exception(
        self, starlite_app: "Starlite", scope: "Scope", receive: "Receive", send: "Send", exc: Exception
    ) -> None:
        """Handle exception raised inside 'http' scope routes.

        :param starlite_app: The starlite app instance.
        :param scope: The ASGI connection scope.
        :param receive: The ASGI receive function.
        :param send: The ASGI send function.
        :param exc: The caught exception.
        :return: None.
        """

        headers = Headers.from_scope(scope=scope)
        if starlite_app.cors_config and (origin := headers.get("origin")):
            cors_middleware = CORSMiddleware(app=self.app, config=starlite_app.cors_config)
            send = cors_middleware.send_wrapper(send=send, origin=origin, has_cookie="cookie" in headers)

        exception_handler = get_exception_handler(self.exception_handlers, exc) or self.default_http_exception_handler
        response = exception_handler(Request(scope=scope, receive=receive, send=send), exc)
        await response(scope=scope, receive=receive, send=send)

    @staticmethod
    async def handle_websocket_exception(send: "Send", exc: Exception) -> None:
        """Handle exception raised inside 'websocket' scope routes.

        :param send: The ASGI send function.
        :param exc: The caught exception.
        :return: None.
        """
        if isinstance(exc, WebSocketException):
            code = exc.code
            reason = exc.detail
        else:
            code = 4000 + getattr(exc, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
            reason = getattr(exc, "detail", repr(exc))
        event: WebSocketCloseEvent = {"type": "websocket.close", "code": code, "reason": reason}
        await send(event)

    def default_http_exception_handler(self, request: Request, exc: Exception) -> Response[Any]:
        """Handle an HTTP exception by returning the appropriate response.

        :param request: An HTTP Request instance.
        :param exc: The caught exception.
        :return: An HTTP response.
        """
        status_code = getattr(exc, "status_code", HTTP_500_INTERNAL_SERVER_ERROR)
        if status_code == HTTP_500_INTERNAL_SERVER_ERROR and self.debug:
            return create_debug_response(request=request, exc=exc)
        return create_exception_response(exc)
