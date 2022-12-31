# Using Middleware

A middleware in Starlite is any callable that receives at least one kwarg called `app` and returns an
[`ASGIApp`][starlite.types.ASGIApp]. Since these terms are somewhat daunting, lets parse what this means: an
`ASGIApp` is nothing but an async function that receives the ASGI primitives - `scope`, `receive` and
`send` - and either calls the next `ASGIApp` or returns a response / handles the websocket connection.

For example, the following function can be used as a middleware because it receives the `app` kwarg and returns
an `ASGIApp`:

```python
from starlite.types import ASGIApp, Scope, Receive, Send


def middleware_factory(app: ASGIApp) -> ASGIApp:
    async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        # do something here
        ...
        await app(scope, receive, send)

    return my_middleware
```

We could then use it by passing it to one of the layers of the application. What does this mean? Unlike other frameworks
that allow users to define middleware only on the application level, Starlite allows users to user middleware on the
different layers of the application. Thus, we could use our middleware on the application layer - like so:

```python
from starlite.types import ASGIApp, Scope, Receive, Send
from starlite import Starlite


def middleware_factory(app: ASGIApp) -> ASGIApp:
    async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        # do something here
        ...
        await app(scope, receive, send)

    return my_middleware


app = Starlite(route_handlers=[...], middleware=[middleware_factory])
```

In the above example, Starlite will call the `middleware_factory` function and pass to it `app`. It's important to
understand that this kwarg does not designate the Starlite application but rather the next `ASGIApp` in the stack. It
will then insert the returned `my_middleware` function into the stack of every route in the application -
because we declared it on the application level.


## Layering Middleware

While running middleware on the application level is the most common use-case, sometimes middleware needs to run on only
a specific subset of routes. Starlite allows doing this by supporting middleware declaration on all layers of the
application - the Starlite instance, routers, controllers and individual route handlers. That is, all of these patterns
are supported as well:

### Router Level Middleware

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

### Controller Level Middleware

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

### Route Handler Level Middleware

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


## Middleware Call Order

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
from starlite.testing.create_test_client import create_test_client


def test_middleware_call_order() -> None:
    """Test that middlewares are called in the order they have been passed."""

    results: list[int] = []

    def create_test_middleware(middleware_id: int) -> type[MiddlewareProtocol]:
        class TestMiddleware(MiddlewareProtocol):
            def __init__(self, app: ASGIApp) -> None:
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


## Passing Args and Kwargs to Middleware

Starlite offers a simple way to pass positional arguments (`*args`) and key-word arguments (`**kwargs`) to middleware
using the [`DefineMiddleware`][starlite.middleware.base.DefineMiddleware] class. Let's extend
the factory function used in the examples above to take some args and kwargs and then use `DefineMiddleware` to pass
these values to our middleware:

```python
from starlite.types import ASGIApp, Scope, Receive, Send
from starlite import Starlite, DefineMiddleware


def middleware_factory(my_arg: int, *, app: ASGIApp, my_kwarg: str) -> ASGIApp:
    async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        # here we can use my_arg and my_kwarg for some purpose
        ...
        await app(scope, receive, send)

    return my_middleware


app = Starlite(
    route_handlers=[...],
    middleware=[DefineMiddleware(middleware_factory, 1, my_kwarg="abc")],
)
```

The `DefineMiddleware` is a simple container - it takes a middleware callable as a first parameter, and then any
positional arguments, followed by key word arguments. The middleware callable will be called with these values as well
as the kwarg `app` as mentioned above.

!!! note
    Starlette also includes a middleware container - `starlette.middleware.Middleware`, and this class is also supported
    by Starlite - so feel free to use it. You should note though that the Starlette class though does not support
    positional arguments.


## Middlewares and Exceptions

When an exception is raised by a route handler or dependency and is then transformed into a response by
an [exception handler](../../17-exceptions#exception-handling), middlewares are still applied to it. The one limitation on
this though are the two exceptions that can be raised by the ASGI router - `404 Not Found` and `405 Method Not Allowed`.
These exceptions are raised before the middleware stack is called, and are only handled by exceptions handlers defined
on the Starlite app instance itself. Thus, if you need to modify the responses generated for these exceptions, you will
need to define a custom exception handler on the app instance level.
