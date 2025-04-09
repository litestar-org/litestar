from docs.examples.security.using_abstract_authentication_middleware.main import MyToken, MyUser

from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.middleware import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)

API_KEY_HEADER = "X-API-KEY"

TOKEN_USER_DATABASE = {"1": "user_authorized"}


class CustomAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, connection: ASGIConnection) -> AuthenticationResult:
        """Given a request, parse the request api key stored in the header and retrieve the user correlating to the token from the DB"""

        # retrieve the auth header
        auth_header = connection.headers.get(API_KEY_HEADER)
        if not auth_header:
            raise NotAuthorizedException()

        # this would be a database call
        token = MyToken(api_key=auth_header)
        user = MyUser(name=TOKEN_USER_DATABASE.get(token.api_key))
        if not user.name:
            raise NotAuthorizedException()
        return AuthenticationResult(user=user, auth=token)
