from litestar import get, Router, Controller, Litestar

class SomeController(Controller):
    path = "/{from_controller:int}"

    @get("/{from_handler:float}")
    async def hello(
            self,
            from_router: str,
            from_controller: int,
            from_handler: float,
    ) -> str:
        return f"Hello {from_router}. Result: {from_controller + from_handler}"


router = Router("/{from_router:str}", route_handlers=[SomeController])
app = Litestar(route_handlers=[router])

# run: /john/1/0.3
