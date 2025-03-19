from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.exceptions import NotAuthorizedException
from litestar.middleware.authentication import (
    AuthenticationResult,
)
from litestar.middleware.base import ASGIAuthenticationMiddleware
from litestar.types import Empty

__all__ = ("SessionAuthMiddleware",)

if TYPE_CHECKING:
    from litestar.connection import ASGIConnection
    from litestar.security.session_auth import SessionAuth


class SessionAuthMiddleware(ASGIAuthenticationMiddleware):
    """Session Authentication Middleware."""

    def __init__(
        self,
        session_auth: SessionAuth,
    ) -> None:
        """Session based authentication middleware.

        Args:
            session_auth: SessionAuth instance.
        """

        self.session_auth = session_auth
        self.retrieve_user_handler = self.session_auth.retrieve_user_handler
        self.exclude_path_pattern = self.session_auth.exclude
        self.exclude_opt_key = self.session_auth.exclude_opt_key
        self.exclude_http_methods = self.session_auth.exclude_http_methods or []

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

        user = await self.retrieve_user_handler(connection.session, connection)  # type: ignore[misc]

        if not user:
            connection.scope["session"] = Empty
            raise NotAuthorizedException("no user correlating to session found")

        return AuthenticationResult(user=user, auth=connection.session)
