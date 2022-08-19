from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Union

from pydantic import BaseConfig, BaseModel
from starlette.requests import HTTPConnection

from starlite.enums import MediaType, ScopeType
from starlite.exceptions import NotAuthorizedException, PermissionDeniedException
from starlite.middleware.base import MiddlewareProtocol
from starlite.response import Response

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send


class AuthenticationResult(BaseModel):
    """This pydantic model is a container for authentication data."""

    user: Any
    """
    The user model, this can be any value corresponding to a user of the API
    """
    auth: Any = None
    """
    The auth value, this can for example be a JWT token.
    """

    class Config(BaseConfig):
        arbitrary_types_allowed = True


class AbstractAuthenticationMiddleware(ABC, MiddlewareProtocol):
    scopes = {ScopeType.HTTP, ScopeType.WEBSOCKET}
    """
    Scopes supported by the middleware.
    """
    error_response_media_type = MediaType.JSON
    """
    The 'Content-Type' to use for error responses.
    """
    websocket_error_status_code = 4000
    """
    The status code to for websocket authentication errors.
    """

    def __init__(self, app: "ASGIApp"):
        """This is an abstract AuthenticationMiddleware that allows users to
        create their own AuthenticationMiddleware by extending it and
        overriding the 'authenticate_request' method.

        Args:
            app: An ASGIApp, this value is the next ASGI handler to call in the middleware stack.
        """
        super().__init__(app)
        self.app = app

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        try:
            if scope["type"] in self.scopes:
                auth_result = await self.authenticate_request(HTTPConnection(scope))
                scope["user"] = auth_result.user
                scope["auth"] = auth_result.auth
            await self.app(scope, receive, send)
        except (NotAuthorizedException, PermissionDeniedException) as e:
            if scope["type"] == ScopeType.WEBSOCKET:  # pragma: no cover
                await send({"type": "websocket.close", "code": self.websocket_error_status_code, "reason": repr(e)})
            else:
                response = self.create_error_response(exc=e)
                await response(scope, receive, send)

    def create_error_response(self, exc: Union[NotAuthorizedException, PermissionDeniedException]) -> Response:
        """Creates an Error response from the given exceptions, defaults to a
        JSON response.

        Args:
            exc: Either an [NotAuthorizedException][starlite.exceptions.NotAuthorizedException] or
                [PermissionDeniedException][starlite.exceptions.PermissionDeniedException] instance.

        Returns:
            A [Response][starlite.response.Response] instance.
        """
        return Response(
            media_type=self.error_response_media_type,
            content={"detail": exc.detail, "extra": exc.extra},
            status_code=exc.status_code,
        )

    @abstractmethod
    async def authenticate_request(self, request: HTTPConnection) -> AuthenticationResult:  # pragma: no cover
        """This method must be overridden by subclasses. It receives the http
        connection and returns an instance of.

        [AuthenticationResult][starlite.middleware.authentication.AuthenticationResult].

        Args:
            request: A Starlette 'HTTPConnection' instance.

        Raises:
            If authentication fail: either an [NotAuthorizedException][starlite.exceptions.NotAuthorizedException] or
                [PermissionDeniedException][starlite.exceptions.PermissionDeniedException] instance.

        Returns:
            [AuthenticationResult][starlite.middleware.authentication.AuthenticationResult]
        """
        raise NotImplementedError("authenticate_request must be overridden by subclasses")
