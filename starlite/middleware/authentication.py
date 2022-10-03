import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, List, Optional, Pattern, Union

from pydantic import BaseConfig, BaseModel

from starlite.connection import ASGIConnection
from starlite.enums import ScopeType

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Receive, Scope, Send


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


class AbstractAuthenticationMiddleware(ABC):
    scopes = {ScopeType.HTTP, ScopeType.WEBSOCKET}
    """
    Scopes supported by the middleware.
    """

    def __init__(
        self,
        app: "ASGIApp",
        exclude: Optional[Union[str, List[str]]] = None,
        exclude_from_auth_key: str = "exclude_from_auth",
    ) -> None:
        """This is an abstract AuthenticationMiddleware that allows users to
        create their own AuthenticationMiddleware by extending it and
        overriding the 'authenticate_request' method.

        Args:
            app: An ASGIApp, this value is the next ASGI handler to call in the middleware stack.
            exclude: A pattern or list of patterns to skip in the authentication middleware.
            exclude_from_auth_key: An identifier to use on routes to disable authentication for a particular route.
        """
        self.app = app
        self.exclude: Optional[Pattern[str]] = None
        self.exclude_from_auth_key = exclude_from_auth_key

        if exclude:
            self.exclude = re.compile("|".join(exclude)) if isinstance(exclude, list) else re.compile(exclude)

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """
        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        exclude_from_auth = scope["route_handler"].opt.get(self.exclude_from_auth_key)
        if (
            not exclude_from_auth
            and (not self.exclude or not self.exclude.findall(scope["path"]))
            and scope["type"] in self.scopes
        ):

            auth_result = await self.authenticate_request(ASGIConnection(scope))
            scope["user"] = auth_result.user
            scope["auth"] = auth_result.auth
        await self.app(scope, receive, send)

    @abstractmethod
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:  # pragma: no cover
        """This method must be overridden by subclasses. It receives the http
        connection and returns an instance of.

        Args:
            connection: An [ASGIConnection][starlite.connection.ASGIConnection] instance.

        Raises:
            NotAuthorizedException | PermissionDeniedException: if authentication fails.

        Returns:
            An instance of [AuthenticationResult][starlite.middleware.authentication.AuthenticationResult].
        """
        raise NotImplementedError("authenticate_request must be overridden by subclasses")
