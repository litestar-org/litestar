# ASGI Route Handlers

<!-- prettier-ignore -->
!!! info
    This feature is available from v0.7.0 onwards

If you need to write your own ASGI application, you can do so using the `asgi` decorator:

```python
from starlette.types import Scope, Receive, Send
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from starlite import Response, asgi


@asgi(path="/my-asgi-app")
async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "http":
        if scope["method"] == "GET":
            response = Response({"hello": "world"}, status_code=HTTP_200_OK)
            await response(scope=scope, receive=receive, send=send)
        return
    response = Response(
        {"detail": "unsupported request"}, status_code=HTTP_400_BAD_REQUEST
    )
    await response(scope=scope, receive=receive, send=send)
```

Using the `asgi` decorator, you receive the maximal amount of control - but this also means that Starlite will not:

1. no dependency injection
2.
