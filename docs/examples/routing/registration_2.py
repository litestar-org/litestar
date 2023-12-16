from litestar import get, Router


@get("/")
async def handler() -> str:
    return "Hello, world!"


router = Router(path="/", route_handlers=[handler])