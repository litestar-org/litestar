from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from litestar import Litestar, asgi
from litestar.types import Scope, Receive, Send


async def index(request: Request) -> PlainTextResponse:
    return PlainTextResponse("hello from starlette")


starlette_app = Starlette(routes=[Route("/", index)])


@asgi("/some/sub-path", is_mount=True)
async def starlette_handler(scope: Scope, receive: Receive, send: Send) -> None:
    await starlette_app(scope=scope, receive=receive, send=send)


app = Litestar(route_handlers=[starlette_handler])
