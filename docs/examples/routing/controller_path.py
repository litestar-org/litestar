from litestar import get, Controller, Litestar


class SomeController(Controller):
    path = "/controller"

    @get("/")
    async def handler() -> str:
        return "Hello, world!"


app = Litestar(route_handlers=[SomeController])