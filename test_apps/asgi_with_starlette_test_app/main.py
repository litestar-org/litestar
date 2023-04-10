from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from litestar import Litestar, asgi, get


@get("/")
async def litestar_index() -> str:
    return "Hello, world!"


async def starlette_index(_: Request) -> PlainTextResponse:
    return PlainTextResponse({"app": "starlette"})


foo_app = asgi(path="/foo", is_mount=True)(Starlette(routes=[Route("/", starlette_index)]))
bar_app = asgi(path="/bar", is_mount=True)(Litestar(route_handlers=[litestar_index]))

app = Litestar(route_handlers=[foo_app, bar_app])

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app)
