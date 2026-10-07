from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar.connection import ASGIConnection
from litestar.enums import HttpMethod, ScopeType
from litestar.middleware.base import ASGIMiddleware

__all__ = ("AbstractAuthenticationMiddleware", "AuthenticationResult")


if TYPE_CHECKING:
    from collections.abc import Sequence

    from litestar.types import ASGIApp, Method, Receive, Scope, Scopes, Send


@dataclass
class AuthenticationResult:
    """Dataclass for authentication result."""

    __slots__ = ("auth", "user")

    user: Any
    """The user model, this can be any value corresponding to a user of the API."""
    auth: Any
    """The auth value, this can for example be a JWT token."""


class AbstractAuthenticationMiddleware(ASGIMiddleware):
    """Abstract AuthenticationMiddleware that allows users to create their own AuthenticationMiddleware by extending it
    and overriding :meth:`AbstractAuthenticationMiddleware.authenticate_request`.
    """

    exclude_opt_key: str | None = "exclude_from_auth"
    """An identifier to use on routes to disable authentication for a particular route."""
    exclude_http_methods: Sequence[Method] = (HttpMethod.OPTIONS,)
    """A sequence of http methods that do not require authentication."""

    def __init__(
        self,
        *,
        exclude: str | list[str] | None = None,
        exclude_from_auth_key: str | None = None,
        exclude_http_methods: Sequence[Method] | None = None,
        scopes: Scopes | None = None,
    ) -> None:
        """Initialize ``AbstractAuthenticationMiddleware``.

        Arguments that are not given fall back to the corresponding class attribute.

        Args:
            exclude: A pattern or list of patterns to skip in the authentication middleware.
            exclude_from_auth_key: An identifier to use on routes to disable authentication for a particular route.
            exclude_http_methods: A sequence of http methods that do not require authentication.
            scopes: ASGI scopes processed by the authentication middleware.
        """
        if exclude is not None:
            self.exclude_path_pattern = (tuple(exclude) if isinstance(exclude, list) else exclude) or None
        if exclude_http_methods is not None:
            self.exclude_http_methods = exclude_http_methods
        if exclude_from_auth_key is not None:
            self.exclude_opt_key = exclude_from_auth_key
        scope_types = set(scopes or self.scopes) | {ScopeType.ASGI}
        self.scopes = tuple(scope_types)
        if scope_types != {ScopeType.HTTP, ScopeType.WEBSOCKET, ScopeType.ASGI}:
            self._scope_bypass_hook = self.should_bypass_for_scope
            self.should_bypass_for_scope = self._should_bypass_for_scope

    def _should_bypass_for_scope(self, scope: Scope) -> bool:
        if scope["type"] not in self.scopes:
            return True
        return self._scope_bypass_hook is not None and self._scope_bypass_hook(scope)

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        """Handle ASGI call.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
            next_app: The next ASGI application in the middleware stack to call.

        Returns:
            None
        """
        if scope.get("method") not in self.exclude_http_methods:
            auth_result = await self.authenticate_request(ASGIConnection(scope))
            scope["user"] = auth_result.user
            scope["auth"] = auth_result.auth
        await next_app(scope, receive, send)

    @abstractmethod
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        """Receive the http connection and return an :class:`AuthenticationResult`.

        Notes:
            - This method must be overridden by subclasses.

        Args:
            connection: An :class:`ASGIConnection <litestar.connection.ASGIConnection>` instance.

        Raises:
            NotAuthorizedException | PermissionDeniedException: if authentication fails.

        Returns:
            An instance of :class:`AuthenticationResult <litestar.middleware.authentication.AuthenticationResult>`.
        """
        raise NotImplementedError("authenticate_request must be overridden by subclasses")
