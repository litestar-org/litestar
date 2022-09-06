import logging
from typing import TYPE_CHECKING

from starlite.connection import Request
from starlite.enums import ScopeType
from starlite.middleware.base import MiddlewareProtocol

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send

    from starlite.logging import LoggingConfig


logger = logging.getLogger(__name__)


class LoggingMiddleware(MiddlewareProtocol):
    def __init__(
        self,
        app: "ASGIApp",
        config: "LoggingConfig",
    ):
        """Logging Middleware class.

        This Middleware log incoming request and outgoing response.

        Args:
            app: The 'next' ASGI app to call.
            config: The LoggingConfig instance.
        """
        super().__init__(app)
        self.app = app
        self.config = config

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["type"] != ScopeType.HTTP:
            await self.app(scope, receive, send)
            return

        request: Request = Request(scope=scope)
        self._log_request(request)

        async def send_wrapper(message: "Message") -> None:  # pylint: disable=used-before-assignment
            if message["type"] == "http.response.start":
                self._log_response(request, message)
            await send(message)

        await self.app(scope, receive, send_wrapper)

    def _log_request(self, request: "Request") -> None:
        """Log following line when request is received.

        '{hostname}:{port} - {method} {path} {scheme}/{http_version} incoming'
        """
        logger.info(
            "%s:%s - %s %s %s/%s incoming",
            request.base_url.hostname,
            request.base_url.port or "",
            request.method.upper(),
            request.base_url.path,
            request.base_url.scheme.upper(),
            request.scope.get("http_version", ""),
        )

    def _log_response(self, request: "Request", message: "Message") -> None:
        """Log following line when response is ready to be sent to client.

        '{hostname}:{port} - {method} {path} {scheme}/{http_version} {result}'
        """
        logger.info(
            "%s:%s - %s %s %s/%s %s",
            request.base_url.hostname,
            request.base_url.port or "",
            request.method.upper(),
            request.base_url.path,
            request.base_url.scheme.upper(),
            request.scope.get("http_version", ""),
            message.get("status", "notset"),
        )
