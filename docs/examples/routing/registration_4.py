from litestar import get, Controller, Litestar


class SomeController(Controller):
    @get("/")
    async def handler(self) -> str:
        return "Hello, world!"


app = Litestar(route_handlers=[SomeController])