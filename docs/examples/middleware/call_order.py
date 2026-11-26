from typing import cast

from litestar import Controller, Litestar, Router, get
from litestar.datastructures import State
from litestar.middleware import ASGIMiddleware
from litestar.types import ASGIApp, Receive, Scope, Send


class TestMiddleware(ASGIMiddleware):
    def __init__(self, middleware_id: int) -> None:
        self.middleware_id = middleware_id

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        litestar_app = scope["app"]
        litestar_app.state.setdefault("middleware_calls", [])
        litestar_app.state["middleware_calls"].append(self.middleware_id)
        await next_app(scope, receive, send)


class MyController(Controller):
    path = "/controller"
    middleware = [TestMiddleware(4), TestMiddleware(5)]

    @get(
        "/handler",
        middleware=[TestMiddleware(6), TestMiddleware(7)],
    )
    async def my_handler(self, state: State) -> list[int]:
        return cast(list[int], state["middleware_calls"])


router = Router(
    path="/router",
    route_handlers=[MyController],
    middleware=[TestMiddleware(2), TestMiddleware(3)],
)

app = Litestar(
    route_handlers=[router],
    middleware=[TestMiddleware(0), TestMiddleware(1)],
)


# run: /router/controller/handler
