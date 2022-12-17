from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List, Optional, Union

from pydantic import BaseConfig, BaseModel

from starlite.connection import ASGIConnection
from starlite.enums import ScopeType
from starlite.middleware.utils import (
    build_exclude_path_pattern,
    should_bypass_middleware,
)

if TYPE_CHECKING:

    from starlite.types import ASGIApp, Receive, Scope, Scopes, Send


class AuthenticationResult(BaseModel):
    """Pydantic model for authentication data."""

    user: Any
    """The user model, this can be any value corresponding to a user of the API."""
    auth: Any = None
    """The auth value, this can for example be a JWT token."""

    class Config(BaseConfig):
        arbitrary_types_allowed = True


class AbstractAuthenticationMiddleware(ABC):
    """Abstract AuthenticationMiddleware that allows users to create their own AuthenticationMiddleware by extending it
    and overriding the 'authenticate_request' method.
    """

    def __init__(
        self,
        app: "ASGIApp",
        exclude: Optional[Union[str, List[str]]] = None,
        exclude_from_auth_key: str = "exclude_from_auth",
        scopes: Optional["Scopes"] = None,
    ) -> None:
        """Initialize `AbstractAuthenticationMiddleware`.

        Args:
            app: An ASGIApp, this value is the next ASGI handler to call in the middleware stack.
            exclude: A pattern or list of patterns to skip in the authentication middleware.
            exclude_from_auth_key: An identifier to use on routes to disable authentication for a particular route.
            scopes: ASGI scopes processed by the authentication middleware.
        """
        self.app = app
        self.scopes = scopes or {ScopeType.HTTP, ScopeType.WEBSOCKET}
        self.exclude_opt_key = exclude_from_auth_key
        self.exclude = build_exclude_path_pattern(exclude=exclude)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        if not should_bypass_middleware(
            scope=scope,
            scopes=self.scopes,
            exclude_path_pattern=self.exclude,
            exclude_opt_key=self.exclude_opt_key,
        ):
            auth_result = await self.authenticate_request(ASGIConnection(scope))
            scope["user"] = auth_result.user
            scope["auth"] = auth_result.auth
        await self.app(scope, receive, send)

    @abstractmethod
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:  # pragma: no cover
        """Receive the http connection and return an `AuthenticationResult`.

        Notes:
            - This method must be overridden by subclasses.

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Raises:
            NotAuthorizedException | PermissionDeniedException: if authentication fails.

        Returns:
            An instance of [AuthenticationResult][starlite.middleware.authentication.AuthenticationResult].
        """
        raise NotImplementedError("authenticate_request must be overridden by subclasses")
