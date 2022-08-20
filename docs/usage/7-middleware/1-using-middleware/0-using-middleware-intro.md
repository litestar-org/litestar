# Using Middleware

A middleware in Starlite is any callable that receives at least one kwarg called `app` and returns an `ASGIApp`. Since
these terms are somewhat daunting, lets parse what this means: an `ASGIApp` is nothing but an async function that receives the
ASGI primitives - `scope`, `receive` and `send` - and either calls the next `ASGIApp` or
returns a response / handles the websocket connection.

For example, the following function can be used as a middleware because it receives the `app` kwarg and returns
an `ASGIApp`:

```python
from starlette.types import ASGIApp, Scope, Receive, Send


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
from starlette.types import ASGIApp, Scope, Receive, Send
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
