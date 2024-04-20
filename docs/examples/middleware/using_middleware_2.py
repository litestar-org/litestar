from litestar.types import ASGIApp, Scope, Receive, Send
from litestar import Litestar


def middleware_factory(app: ASGIApp) -> ASGIApp:
    async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        # do something here
        ...
        await app(scope, receive, send)

    return my_middleware


app = Litestar(route_handlers=[...], middleware=[middleware_factory])