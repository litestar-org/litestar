from typing import TYPE_CHECKING, List, Type

from starlite import Controller, Router, Starlite, get
from starlite.datastructures import State
from starlite.middleware import MiddlewareProtocol

if TYPE_CHECKING:
    from starlite.types import ASGIApp, Receive, Scope, Send


def create_test_middleware(middleware_id: int) -> Type[MiddlewareProtocol]:
    class TestMiddleware(MiddlewareProtocol):
        def __init__(self, app: "ASGIApp") -> None:
            self.app = app

        async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
            starlite_app = scope["app"]
            starlite_app.state.setdefault("middleware_calls", [])
            starlite_app.state["middleware_calls"].append(middleware_id)
            await self.app(scope, receive, send)

    return TestMiddleware


class MyController(Controller):
    path = "/controller"
    middleware = [create_test_middleware(4), create_test_middleware(5)]

    @get(
        "/handler",
        middleware=[create_test_middleware(6), create_test_middleware(7)],
    )
    async def my_handler(self, state: State) -> List[int]:
        return state["middleware_calls"]


router = Router(
    path="/router",
    route_handlers=[MyController],
    middleware=[create_test_middleware(2), create_test_middleware(3)],
)

app = Starlite(
    route_handlers=[router],
    middleware=[create_test_middleware(0), create_test_middleware(1)],
)


# run: /router/controller/handler
