# Middleware Call Order

The call order of middleware follows a simple rule: _middleware is called top to bottom, left to right_.

That is to say- application level middleware will be called before router level middleware, which will be called
before controller level middleware, which will be called before route handler middleware. And also, that middleware
defined first the in the middleware list, will be called first. To illustrate this, consider the following test case:

```python
from starlite.types import ASGIApp, Receive, Scope, Send

from starlite import (
    Controller,
    MiddlewareProtocol,
    Router,
    get,
)
from starlite.testing import create_test_client


def test_middleware_call_order() -> None:
    """Test that middlewares are called in the order they have been passed."""

    results: list[int] = []

    def create_test_middleware(middleware_id: int) -> type[MiddlewareProtocol]:
        class TestMiddleware(MiddlewareProtocol):
            def __init__(self, app: ASGIApp):
                self.app = app

            async def __call__(
                self, scope: Scope, receive: Receive, send: Send
            ) -> None:
                results.append(middleware_id)
                await self.app(scope, receive, send)

        return TestMiddleware

    class MyController(Controller):
        path = "/controller"
        middleware = [create_test_middleware(4), create_test_middleware(5)]

        @get(
            "/handler",
            middleware=[create_test_middleware(6), create_test_middleware(7)],
        )
        def my_handler(self) -> None:
            return None

    router = Router(
        path="/router",
        route_handlers=[MyController],
        middleware=[create_test_middleware(2), create_test_middleware(3)],
    )

    with create_test_client(
        route_handlers=[router],
        middleware=[create_test_middleware(0), create_test_middleware(1)],
    ) as client:
        client.get("/router/controller/handler")

        assert results == [0, 1, 2, 3, 4, 5, 6, 7]
```
