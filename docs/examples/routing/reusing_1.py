from litestar import get, Litestar, Router


@get("/")
async def handler() -> str:
    return "Hello, world!"


router_a = Router(path="/a", route_handlers=[handler])
router_b = Router(path="/b", route_handlers=[handler])

app = Litestar(route_handlers=[router_a, router_b])