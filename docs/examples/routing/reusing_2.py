from litestar import get, Controller, Litestar, Router


class SomeController(Controller):
    @get("/")
    async def handler(self) -> str:
        return "Hello, world!"


router_a = Router(path="/a", route_handlers=[SomeController])
router_b = Router(path="/b", route_handlers=[SomeController])

app = Litestar(route_handlers=[router_a, router_b])