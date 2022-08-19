# Layering Middleware

While running middleware on the application level is the most common use-case, sometimes middleware needs to run on only
a specific subset of routes. Starlite allows doing this by supporting middleware declaration on all layers of the
application - the Starlite instance, routers, controllers and individual route handlers. That is, all of these patterns
are supported as well:

## Router Level Middleware

By passing middleware on the router, this middleware will be used for all routes on the router:

```python
from starlite.types import ASGIApp, Scope, Receive, Send
from starlite import Starlite, Router, get


def middleware_factory(app: ASGIApp) -> ASGIApp:
    async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        ...
        await app(scope, receive, send)

    return my_middleware


@get("/handler1")
def handler1(self) -> dict[str, str]:
    ...


@get("/handler2")
def handler2(self) -> dict[str, str]:
    ...


router = Router(
    path="/router", route_handlers=[handler1, handler2], middleware=[middleware_factory]
)

app = Starlite(route_handlers=[router])
```

## Controller Level Middleware

By passing middleware on the controller, this middleware will be used for all routes on the controller:

```python
from starlite.types import ASGIApp, Scope, Receive, Send
from starlite import Starlite, Controller, get


def middleware_factory(app: ASGIApp) -> ASGIApp:
    async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        ...
        await app(scope, receive, send)

    return my_middleware


class MyController(Controller):
    path = "/controller"
    middleware = [middleware_factory]

    @get("/handler1")
    def handler1(self) -> dict[str, str]:
        ...

    @get("/handler2")
    def handler2(self) -> dict[str, str]:
        ...


app = Starlite(route_handlers=[MyController], middleware=[middleware_factory])
```

## Route Handler Level Middleware

By passing middleware on the route handler, this middleware will be used only for those route handlers that specify it:

```python
from starlite.types import ASGIApp, Scope, Receive, Send
from starlite import Starlite, get


def middleware_factory(app: ASGIApp) -> ASGIApp:
    async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        ...
        await app(scope, receive, send)

    return my_middleware


@get("/handler1", middleware=[middleware_factory])
def handler1(self) -> dict[str, str]:
    ...


@get("/handler2")
def handler2(self) -> dict[str, str]:
    ...


app = Starlite(route_handlers=[handler1, handler2])
```
