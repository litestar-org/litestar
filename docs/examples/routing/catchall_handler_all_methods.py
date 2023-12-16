from litestar import get, Litestar, route
from litestar.enums import HttpMethod


@get("/hello")
async def hello() -> str:
    return "Hello, world!"


@route("/{path:path}", http_method=HttpMethod)
async def catchall(path: str) -> str:
    return path


app = Litestar(route_handlers=[hello, catchall])

# run: /some/path -X GET
# run: /some/path -X POST
# run: /some/path -X PATCH
