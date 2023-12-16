from litestar import get, Litestar, Router


@get("/handler")
async def handler() -> str:
    return "Hello, world!"


router = Router(path="/router", route_handlers=[handler])
app = Litestar(route_handlers=[router])