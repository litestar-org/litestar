from litestar import get, Router, Litestar


@get("/")
async def handler() -> str:
    return "Hello, world!"


router = Router(path="/", route_handlers=[handler])
app = Litestar(route_handlers=[router])