from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from litestar import Litestar, asgi


async def index(request: Request) -> PlainTextResponse:
    return PlainTextResponse("hello from starlette")


starlette_app = Starlette(routes=[Route("/", index)])


starlette_handler = asgi("/some/sub-path", is_mount=True)(starlette_app)


app = Litestar(route_handlers=[starlette_handler])
