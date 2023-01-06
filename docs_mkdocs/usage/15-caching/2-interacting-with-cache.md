# Interacting with the Cache

The Starlite app's cache is exposed as `app.cache`, which makes it accessible via the `scope` object. For example, you
can access the cache in a custom middleware thus:

```python
from starlite import MiddlewareProtocol
from starlite.types import Scope, Receive, Send, ASGIApp


class MyMiddleware(MiddlewareProtocol):
    def __init__(self, app: ASGIApp):
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        cached_value = await scope["app"].cache.get("my-key")
        if cached_value:
            ...
```

The cache is also exposed as a property on the [`ASGIConnection`][starlite.connection.ASGIConnection] and the
[`Request`][starlite.connection.Request] and [`WebSocket`][starlite.connection.WebSocket] classes that inherit from it.
You can thus interact with the cache inside a route handler easily, for example by doing this:

```python
from starlite import Request, get


@get("/")
async def my_handler(request: Request) -> None:
    cached_value = await request.cache.get("my-key")
    if cached_value:
        ...
```

!!! important
    Cache based operations are async because async locking is used to protect against race conditions. If you need to use
    caching - use an async route handler.
