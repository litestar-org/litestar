from litestar.middleware import (
    AbstractAuthenticationMiddleware,
    AuthenticationResult,
)
from litestar.connection import ASGIConnection


class MyAuthenticationMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(
            self, connection: ASGIConnection
    ) -> AuthenticationResult:
        # do something here.
        ...
