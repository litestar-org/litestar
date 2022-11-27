from typing import TYPE_CHECKING, Awaitable, List, Optional, Union

from starlite import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
    NotAuthorizedException,
)
from starlite.connection import ASGIConnection
from starlite.contrib.jwt.jwt_token import Token

if TYPE_CHECKING:
    from typing import Any

    from starlite.types import ASGIApp
    from starlite.utils import AsyncCallable


class JWTAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    """JWT Authentication middleware.

    This class provides JWT authentication functionalities.
    """

    def __init__(
        self,
        app: "ASGIApp",
        exclude: Optional[Union[str, List[str]]],
        algorithm: str,
        auth_header: str,
        retrieve_user_handler: Union[
            "AsyncCallable[[Any, ASGIConnection[Any, Any, Any]], Awaitable[Any]]",
            "AsyncCallable[[Any], Awaitable[Any]]",
        ],
        token_secret: str,
    ):
        """Check incoming requests for an encoded token in the auth header specified, and if present retrieves the user
        from persistence using the provided function.

        Args:
            app: An ASGIApp, this value is the next ASGI handler to call in the middleware stack.
            retrieve_user_handler: A function that receives an instance of 'Token' and returns a user, which can be
                any arbitrary value.
            token_secret: Secret for decoding the JWT token. This value should be equivalent to the secret used to encode it.
            auth_header: Request header key from which to retrieve the token. E.g. 'Authorization' or 'X-Api-Key'.
            algorithm: JWT hashing algorithm to use.
            exclude: A pattern or list of patterns to skip.
        """
        super().__init__(app=app, exclude=exclude)
        self.algorithm = algorithm
        self.auth_header = auth_header
        self.retrieve_user_handler = retrieve_user_handler
        self.token_secret = token_secret

    async def authenticate_request(self, connection: "ASGIConnection[Any,Any,Any]") -> AuthenticationResult:
        """Given an HTTP Connection, parse the JWT api key stored in the header and retrieve the user correlating to the
        token from the DB.

        Args:
            connection: An Starlite HTTPConnection instance.

        Returns:
            AuthenticationResult

        Raises:
            [NotAuthorizedException][starlite.exceptions.NotAuthorizedException]: If token is invalid or user is not found.
        """
        auth_header = connection.headers.get(self.auth_header)
        if not auth_header:
            raise NotAuthorizedException("No JWT token found in request header")
        _, _, encoded_token = auth_header.partition(" ")
        return await self.authenticate_token(encoded_token=encoded_token, connection=connection)

    async def authenticate_token(
        self, encoded_token: str, connection: "ASGIConnection[Any, Any, Any]"
    ) -> AuthenticationResult:
        """Given an encoded JWT token, parse, validate and look up sub within token.

        Args:
            encoded_token: _description_
            connection: An ASGI connection instance.

        Raises:
            [NotAuthorizedException][starlite.exceptions.NotAuthorizedException]: If token is invalid or user is not found.

        Returns:
            AuthenticationResult: _description_
        """
        token = Token.decode(
            encoded_token=encoded_token,
            secret=self.token_secret,
            algorithm=self.algorithm,
        )
        if self.retrieve_user_handler.num_expected_args == 2:
            user = await self.retrieve_user_handler(token.sub, connection)  # type: ignore[call-arg]
        else:
            user = await self.retrieve_user_handler(token.sub)  # type: ignore[call-arg]

        if not user:
            raise NotAuthorizedException()

        return AuthenticationResult(user=user, auth=token)


class JWTCookieAuthenticationMiddleware(JWTAuthenticationMiddleware):
    """Cookie based JWT authentication middleware."""

    def __init__(
        self,
        app: "ASGIApp",
        exclude: Optional[Union[str, List[str]]],
        algorithm: str,
        auth_header: str,
        auth_cookie_key: str,
        retrieve_user_handler: Union[
            "AsyncCallable[[Any, ASGIConnection[Any, Any, Any]], Awaitable[Any]]",
            "AsyncCallable[[Any], Awaitable[Any]]",
        ],
        token_secret: str,
    ):
        """Check incoming requests for an encoded token in the auth header or cookie name specified, and if present
        retrieves the user from persistence using the provided function.

        Args:
            app: An ASGIApp, this value is the next ASGI handler to call in the middleware stack.
            retrieve_user_handler: A function that receives an instance of 'Token' and returns a user, which can be
                any arbitrary value.
            token_secret: Secret for decoding the JWT token. This value should be equivalent to the secret used to encode it.
            auth_header: Request header key from which to retrieve the token. E.g. 'Authorization' or 'X-Api-Key'.
            auth_cookie_key: Cookie name from which to retrieve the token. E.g. 'token' or 'accessToken'.
            algorithm: JWT hashing algorithm to use.
            exclude: A pattern or list of patterns to skip.
        """
        super().__init__(
            algorithm=algorithm,
            app=app,
            auth_header=auth_header,
            retrieve_user_handler=retrieve_user_handler,
            token_secret=token_secret,
            exclude=exclude,
        )

        self.auth_cookie_key = auth_cookie_key

    async def authenticate_request(self, connection: "ASGIConnection[Any,Any,Any]") -> AuthenticationResult:
        """Given an HTTP Connection, parse the JWT api key stored in the header and retrieve the user correlating to the
        token from the DB.

        Args:
            connection: An Starlite HTTPConnection instance.

        Returns:
            AuthenticationResult

        Raises:
            [NotAuthorizedException][starlite.exceptions.NotAuthorizedException]: If token is invalid or user is not found.
        """
        auth_header = connection.headers.get(self.auth_header) or connection.cookies.get(self.auth_cookie_key)
        if not auth_header:
            raise NotAuthorizedException("No JWT token found in request header or cookies")
        _, _, encoded_token = auth_header.partition(" ")
        return await self.authenticate_token(encoded_token=encoded_token, connection=connection)
