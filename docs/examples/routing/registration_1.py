from litestar import get, Litestar

@get("/")
async def handler() -> str:
    return "Hello, world!"


app = Litestar(route_handlers=[handler])