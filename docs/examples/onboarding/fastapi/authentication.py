from litestar import Litestar, get
from litestar.connection import ASGIConnection
from litestar.exceptions import NotAuthorizedException
from litestar.handlers import BaseRouteHandler


async def require_token(connection: ASGIConnection, route_handler: BaseRouteHandler) -> None:
    if connection.headers.get("authorization") != "Bearer secret":
        raise NotAuthorizedException


@get("/", guards=[require_token])
async def index() -> dict[str, str]:
    return {"hello": "world"}


app = Litestar(route_handlers=[index])
