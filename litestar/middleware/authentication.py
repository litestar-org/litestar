from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from litestar.connection import ASGIConnection
from litestar.enums import HttpMethod, ScopeType
from litestar.middleware._utils import (
    build_exclude_path_pattern,
    should_bypass_middleware,
)

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


class AbstractAuthenticationMiddleware(ABC):
    """Abstract AuthenticationMiddleware that allows users to create their own AuthenticationMiddleware by extending it
    and overriding :meth:`AbstractAuthenticationMiddleware.authenticate_request`.
    """

    __slots__ = (
        "app",
        "exclude",
        "exclude_http_methods",
        "exclude_opt_key",
        "scopes",
    )

    def __init__(
        self,
        app: ASGIApp,
        exclude: str | list[str] | None = None,
        exclude_from_auth_key: str = "exclude_from_auth",
        exclude_http_methods: Sequence[Method] | None = None,
        scopes: Scopes | None = None,
    ) -> None:
        """Initialize ``AbstractAuthenticationMiddleware``.

        Args:
            app: An ASGIApp, this value is the next ASGI handler to call in the middleware stack.
            exclude: A pattern or list of patterns to skip in the authentication middleware.
            exclude_from_auth_key: An identifier to use on routes to disable authentication for a particular route.
            exclude_http_methods: A sequence of http methods that do not require authentication.
            scopes: ASGI scopes processed by the authentication middleware.
        """
        self.app = app
        self.exclude = build_exclude_path_pattern(exclude=exclude, middleware_cls=type(self))
        self.exclude_http_methods = (HttpMethod.OPTIONS,) if exclude_http_methods is None else exclude_http_methods
        self.exclude_opt_key = exclude_from_auth_key
        self.scopes = scopes or {ScopeType.HTTP, ScopeType.WEBSOCKET}

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        if not should_bypass_middleware(
            exclude_http_methods=self.exclude_http_methods,
            exclude_opt_key=self.exclude_opt_key,
            exclude_path_pattern=self.exclude,
            scope=scope,
            scopes=self.scopes,
        ):
            auth_result = await self.authenticate_request(ASGIConnection(scope))
            scope["user"] = auth_result.user
            scope["auth"] = auth_result.auth
        await self.app(scope, receive, send)

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


class ASGIAuthenticationMiddleware(ABC):
    """ASGI Authentication Middleware that allows users to create their own authentication middleware by extending it
    and overriding :meth:`ASGIAuthenticationMiddleware.authenticate_request`.
    """
    __slots__ = ("jwt_auth", "auth_cookie_key",)

    scopes: tuple[ScopeType, ...] = (ScopeType.HTTP, ScopeType.WEBSOCKET, ScopeType.ASGI)
    exclude_path_pattern: str | tuple[str, ...] | None = None
    exclude_opt_key: str = "exclude_from_auth"
    exclude_http_methods: Sequence[Method] = (HttpMethod.OPTIONS,)

    def __call__(self, app: ASGIApp) -> ASGIApp:
        """Create the actual middleware callable"""
        authenticate_request = self.authenticate_request
        exclude_pattern = build_exclude_path_pattern(exclude=self.exclude_path_pattern, middleware_cls=type(self))
        scopes = set(self.scopes)
        exclude_opt_key = self.exclude_opt_key
        exclude_http_methods = self.exclude_http_methods

        async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
            if not should_bypass_middleware(
                exclude_http_methods=exclude_http_methods,
                exclude_opt_key=exclude_opt_key,
                exclude_path_pattern=exclude_pattern,
                scope=scope,
                scopes=scopes,  # type: ignore[arg-type]
            ):
                auth_result = await authenticate_request(ASGIConnection(scope))
                scope["user"] = auth_result.user
                scope["auth"] = auth_result.auth
            await app(scope, receive, send)

        return middleware

    @abstractmethod
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        """Receive the ASGI connection and return an :class:`AuthenticationResult`.

        Notes:
            - This method must be overridden by subclasses.

        Args:
            connection: An :class:`ASGIConnection <litestar.connection.ASGIConnection>` instance.

        Raises:
            NotAuthorizedException | PermissionDeniedException: if authentication fails.

        Returns:
            An instance of :class:`AuthenticationResult <litestar.middleware.authentication.AuthenticationResult>`.
        """
        raise NotImplementedError("handle must be overridden by subclasses")
