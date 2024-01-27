from litestar import get, Litestar


@get("/hello")
async def hello() -> str:
    return "Hello, world!"


@get("/{path:path}")
async def catchall(path: str) -> str:
    return path


app = Litestar(route_handlers=[hello, catchall])


# run: /hello
# run: /hello/something
# run: /some-other/path/with/more/segments
