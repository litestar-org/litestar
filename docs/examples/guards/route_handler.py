from litestar import get
from litestar.exceptions import NotAuthorizedException
from litestar.connection import ASGIConnection
from litestar.handlers.base import BaseRouteHandler
from os import environ


def secret_token_guard(
        connection: ASGIConnection, route_handler: BaseRouteHandler
) -> None:
    if (
            route_handler.opt.get("secret")
            and not connection.headers.get("Secret-Header", "")
                    == route_handler.opt["secret"]
    ):
        raise NotAuthorizedException()


@get(path="/secret", guards=[secret_token_guard], opt={"secret": environ.get("SECRET")})
def secret_endpoint() -> None: ...