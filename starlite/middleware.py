from abc import ABC, abstractmethod
from typing import Any, Dict, Union

from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.requests import HTTPConnection
from starlette.responses import Response as StarletteResponse
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp, Receive, Scope, Send
from typing_extensions import Type

from starlite.connection import Request
from starlite.enums import MediaType, ScopeType
from starlite.exceptions import (
    HTTPException,
    NotAuthorizedException,
    PermissionDeniedException,
)
from starlite.response import Response
from starlite.types import ExceptionHandler, MiddlewareProtocol
from starlite.utils.exception import get_exception_handler


class AuthenticationResult(BaseModel):
    user: Any
    auth: Any = None

    class Config:
        arbitrary_types_allowed = True


class AbstractAuthenticationMiddleware(ABC, MiddlewareProtocol):
    scopes = {ScopeType.HTTP, ScopeType.WEBSOCKET}

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        try:
            if scope["type"] in self.scopes:
                auth_result = await self.authenticate_request(HTTPConnection(scope))
                scope["user"] = auth_result.user
                scope["auth"] = auth_result.auth
            await self.app(scope, receive, send)
        except (NotAuthorizedException, PermissionDeniedException) as e:
            if scope["type"] == ScopeType.WEBSOCKET:  # pragma: no cover
                # we use a custom error code
                status_code = e.status_code + 4000
                await send({"type": "websocket.close", "code": status_code, "reason": repr(e)})
            response = self.create_error_response(exc=e)
            await response(scope, receive, send)
        return None

    @staticmethod
    def create_error_response(exc: Union[NotAuthorizedException, PermissionDeniedException]) -> Response:
        """Creates an Error response from the given exceptions, defaults to a JSON response"""
        return Response(
            media_type=MediaType.JSON,
            content={"detail": exc.detail, "extra": exc.extra},
            status_code=exc.status_code,
        )

    @abstractmethod
    async def authenticate_request(self, request: HTTPConnection) -> AuthenticationResult:  # pragma: no cover
        """
        Given a request, return an instance of AuthenticationResult
        containing a user and any relevant auth context, e.g. a JWT token.

        If authentication fails, raise an HTTPException, e.g. starlite.exceptions.NotAuthorizedException
        or starlite.exceptions.PermissionDeniedException
        """
        raise NotImplementedError("authenticate_request must be overridden by subclasses")


class ExceptionHandlerMiddleware(MiddlewareProtocol):
    def __init__(
        self, app: ASGIApp, debug: bool, exception_handlers: Dict[Union[int, Type[Exception]], ExceptionHandler]
    ):
        self.app = app
        self.exception_handlers = exception_handlers
        self.debug = debug

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:  # pragma: no cover
        """
        Wraps self.app inside a try catch block and handles any exceptions raised
        """
        try:
            await self.app(scope, receive, send)
        except Exception as exc:  # pylint: disable=broad-except
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

    def default_http_exception_handler(self, request: Request, exc: Exception) -> StarletteResponse:
        """Default handler for exceptions subclassed from HTTPException"""
        status_code = exc.status_code if isinstance(exc, StarletteHTTPException) else HTTP_500_INTERNAL_SERVER_ERROR
        if status_code == HTTP_500_INTERNAL_SERVER_ERROR and self.debug:
            # in debug mode, we just use the serve_middleware to create an HTML formatted response for us
            server_middleware = ServerErrorMiddleware(app=self)
            return server_middleware.debug_response(request=request, exc=exc)
        if isinstance(exc, HTTPException):
            content = {"detail": exc.detail, "extra": exc.extra, "status_code": exc.status_code}
        elif isinstance(exc, StarletteHTTPException):
            content = {"detail": exc.detail, "status_code": exc.status_code}
        else:
            content = {"detail": repr(exc)}
        return Response(
            media_type=MediaType.JSON,
            content=content,
            status_code=status_code,
        )
