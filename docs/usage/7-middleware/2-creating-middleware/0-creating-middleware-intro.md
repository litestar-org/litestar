# Creating Middleware

As mentioned in the [using middleware](../1-using-middleware/0-using-middleware-intro.md) section, a middleware in Starlite
is **any callable** that takes a kwarg called `app`, which is the next ASGI handler, i.e. an `ASGIApp`, and returns an `ASGIApp`.

The example previously given was using a factory function, i.e.:

```python
from starlette.types import ASGIApp, Scope, Receive, Send


def middleware_factory(app: ASGIApp) -> ASGIApp:
    async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
        # do something here
        ...
        await app(scope, receive, send)

    return my_middleware
```

While using functions is a perfectly viable approach, you can also use classes to do the same. See the next sections on
two base classes you can use for this purpose - the Starlette [BaseHTTPMiddleware](1-using-basehttp-middleware.md) or the
Starlite [MiddlewareProtocol](2-using-middleware-protocol.md).
