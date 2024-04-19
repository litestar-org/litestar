from litestar import Litestar, get, ASGIConnection, BaseRouteHandler


async def authenticate(
        connection: ASGIConnection, route_handler: BaseRouteHandler
) -> None: ...


@get("/", guards=[authenticate])
async def index() -> dict[str, str]: ...