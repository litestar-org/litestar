from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.exceptions import NotAuthorizedException
from litestar.middleware._internal.exceptions import ExceptionHandlerMiddleware
from litestar.middleware.authentication import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.types import Empty, Method, Scopes
from litestar.utils.sync import ensure_async_callable

__all__ = ("SessionAuthMiddleware",)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Sequence

    from litestar.connection import ASGIConnection
    from litestar.types import ASGIApp, SyncOrAsyncUnion


class SessionAuthMiddleware(AbstractAuthenticationMiddleware):
    """Session Authentication Middleware."""

    def __init__(
        self,
        *,
        exclude: str | list[str] | None,
        exclude_http_methods: Sequence[Method] | None,
        exclude_opt_key: str,
        retrieve_user_handler: Callable[[dict[str, Any], ASGIConnection[Any, Any, Any, Any]], SyncOrAsyncUnion[Any]],
        scopes: Scopes | None,
    ) -> None:
        """Session based authentication middleware.

        Args:
            exclude: A pattern or list of patterns to skip in the authentication middleware.
            exclude_http_methods: A sequence of http methods that do not require authentication.
            exclude_opt_key: An identifier to use on routes to disable authentication and authorization checks for a particular route.
            scopes: ASGI scopes processed by the authentication middleware.
            retrieve_user_handler: Callable that receives the ``session`` value from the authentication middleware and returns a ``user`` value.
        """
        super().__init__(
            exclude=exclude,
            exclude_from_auth_key=exclude_opt_key,
            exclude_http_methods=exclude_http_methods,
            scopes=scopes,
        )
        self.retrieve_user_handler: Callable[[dict[str, Any], ASGIConnection[Any, Any, Any, Any]], Awaitable[Any]] = (
            ensure_async_callable(retrieve_user_handler)
        )

    def __call__(self, app: ASGIApp) -> ASGIApp:
        """Wrap the authentication middleware in an exception handler, so that a failed authentication is turned into a
        response by the session middleware's send wrapper and the session gets cleared.

        Args:
            app: The next ASGI application in the middleware stack.

        Returns:
            The wrapped ASGI application.
        """
        return ExceptionHandlerMiddleware(app=super().__call__(app))

    async def authenticate_request(self, connection: ASGIConnection[Any, Any, Any, Any]) -> AuthenticationResult:
        """Authenticate an incoming connection.

        Args:
            connection: An :class:`ASGIConnection <.connection.ASGIConnection>` instance.

        Raises:
            NotAuthorizedException: if session data is empty or user is not found.

        Returns:
            :class:`AuthenticationResult <.middleware.authentication.AuthenticationResult>`
        """
        if not connection.session or connection.scope["session"] is Empty:
            # the assignment of 'Empty' forces the session middleware to clear session data.
            connection.scope["session"] = Empty
            raise NotAuthorizedException("no session data found")

        user = await self.retrieve_user_handler(connection.session, connection)

        if not user:
            connection.scope["session"] = Empty
            raise NotAuthorizedException("no user correlating to session found")

        return AuthenticationResult(user=user, auth=connection.session)
