# Passing Args and Kwargs to Middleware

Starlite offers a simple way to pass positional arguments (`*args`) and key-word arguments (`**kwargs`) to middleware
using the `starlite.middleware.base.DefineMiddleware` class. Let's extend the factory function used in the examples above
to take some args and kwargs and then use `DefineMiddleware` to pass these values to our middleware:

```python
from starlette.types import ASGIApp, Scope, Receive, Send
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
