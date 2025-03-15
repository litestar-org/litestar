from __future__ import annotations

import asyncio
from asyncio import iscoroutinefunction
from typing import TYPE_CHECKING

from litestar.exceptions import NotAuthorizedException
from litestar.middleware.authentication import (
    ASGIAuthenticationMiddleware,
    AuthenticationResult,
)

__all__ = ("JWTAuthenticationMiddleware", "JWTCookieAuthenticationMiddleware")


if TYPE_CHECKING:
    from typing import Any

    from litestar.connection import ASGIConnection
    from litestar.security.jwt import JWTAuth, JWTCookieAuth


class JWTAuthenticationMiddleware(ASGIAuthenticationMiddleware):
    """JWT Authentication middleware.

    This middleware checks incoming requests for an encoded token in the auth header specified, and if present retrieves
    """

    def __init__(
        self,
        jwt_auth: JWTAuth,
    ) -> None:
        """Check incoming requests for an encoded token in the auth header specified, and if present retrieve the user
        from persistence using the provided function.

        Args:
            jwt_auth: JWTAuth instance.
        """
        self.jwt_auth = jwt_auth
        self.exclude_path_pattern = self.jwt_auth.exclude
        self.exclude_opt_key = self.jwt_auth.exclude_opt_key
        self.exclude_http_methods = self.jwt_auth.exclude_http_methods or []

    async def authenticate_request(self, connection: ASGIConnection[Any, Any, Any, Any]) -> AuthenticationResult:
        """Given an HTTP Connection, parse the JWT api key stored in the header and retrieve the user correlating to the
        token from the DB.

        Args:
            connection: An Litestar HTTPConnection instance.

        Returns:
            AuthenticationResult

        Raises:
            NotAuthorizedException: If token is invalid or user is not found.
        """
        auth_header = connection.headers.get(self.jwt_auth.auth_header)
        if not auth_header:
            raise NotAuthorizedException("No JWT token found in request header")
        encoded_token = auth_header.partition(" ")[-1]
        return await self.authenticate_token(encoded_token=encoded_token, connection=connection)

    async def authenticate_token(
        self, encoded_token: str, connection: ASGIConnection[Any, Any, Any, Any]
    ) -> AuthenticationResult:
        """Given an encoded JWT token, parse, validate and look up sub within token.

        Args:
            encoded_token: Encoded JWT token.
            connection: An ASGI connection instance.

        Raises:
            NotAuthorizedException: If token is invalid or user is not found.

        Returns:
            AuthenticationResult
        """
        token = self.jwt_auth.token_cls.decode(
            encoded_token=encoded_token,
            secret=self.jwt_auth.token_secret,
            algorithm=self.jwt_auth.algorithm,
            audience=self.jwt_auth.accepted_audiences,
            issuer=self.jwt_auth.accepted_issuers,
            require_claims=self.jwt_auth.require_claims,
            verify_exp=self.jwt_auth.verify_expiry,
            verify_nbf=self.jwt_auth.verify_not_before,
            strict_audience=self.jwt_auth.strict_audience,
        )

        user = (
            await self.jwt_auth.retrieve_user_handler(token, connection)
            if asyncio.iscoroutinefunction(self.jwt_auth.retrieve_user_handler)
            else self.jwt_auth.retrieve_user_handler(token, connection)
        )

        if self.jwt_auth.revoked_token_handler:
            token_revoked = (
                await self.jwt_auth.revoked_token_handler(token, connection)
                if iscoroutinefunction(self.jwt_auth.revoked_token_handler)
                else self.jwt_auth.revoked_token_handler(token, connection)
            )
        else:
            token_revoked = False

        if not user or token_revoked:
            raise NotAuthorizedException()

        return AuthenticationResult(user=user, auth=token)


class JWTCookieAuthenticationMiddleware(JWTAuthenticationMiddleware):
    """Cookie based JWT authentication middleware.

    This middleware checks incoming requests for an encoded token in the auth header or cookie name specified, and if
    present retrieves the user from persistence using the provided function.
    """

    def __init__(
        self,
        jwt_cookie_auth: JWTCookieAuth,
    ) -> None:
        """Check incoming requests for an encoded token in the auth header or cookie name specified, and if present
        retrieves the user from persistence using the provided function.

        Args:
            jwt_cookie_auth: JWTAuth instance.
        """
        self.jwt_auth = jwt_cookie_auth  # type: ignore[assignment]
        self.auth_cookie_key = jwt_cookie_auth.key
        self.exclude_path_pattern = self.jwt_auth.exclude
        self.exclude_opt_key = self.jwt_auth.exclude_opt_key
        self.exclude_http_methods = self.jwt_auth.exclude_http_methods or []

    async def authenticate_request(self, connection: ASGIConnection[Any, Any, Any, Any]) -> AuthenticationResult:
        """Given an HTTP Connection, parse the JWT api key stored in the header and retrieve the user correlating to the
        token from the DB.

        Args:
            connection: An Litestar HTTPConnection instance.

        Raises:
            NotAuthorizedException: If token is invalid or user is not found.

        Returns:
            AuthenticationResult
        """
        auth_header = connection.headers.get(self.jwt_auth.auth_header) or connection.cookies.get(self.auth_cookie_key)
        if not auth_header:
            raise NotAuthorizedException("No JWT token found in request header or cookies")
        encoded_token = auth_header.partition(" ")[-1]
        return await self.authenticate_token(encoded_token=encoded_token, connection=connection)
