# ASGI Route Handlers

If you need to write your own ASGI application, you can do so using the `asgi` decorator:

```python
from starlite.types import Scope, Receive, Send
from starlite.enums import MediaType
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from starlite import Response, asgi


@asgi(path="/my-asgi-app")
async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "http":
        if scope["method"] == "GET":
            response = Response(
                {"hello": "world"}, status_code=HTTP_200_OK, media_type=MediaType.JSON
            )
            await response(scope=scope, receive=receive, send=send)
        return
    response = Response(
        {"detail": "unsupported request"},
        status_code=HTTP_400_BAD_REQUEST,
        media_type=MediaType.JSON,
    )
    await response(scope=scope, receive=receive, send=send)
```

Like other route handlers, the `asgi` decorator is an alias of the class `starlite.handlers.asgi.ASGIRouteHandler`. Thus,
the code below is equivalent to the one above:

```python
from starlite.types import Scope, Receive, Send
from starlite.enums import MediaType
from starlette.status import HTTP_200_OK, HTTP_400_BAD_REQUEST
from starlite import ASGIRouteHandler, Response


@ASGIRouteHandler(path="/my-asgi-app")
async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
    if scope["type"] == "http":
        if scope["method"] == "GET":
            response = Response(
                {"hello": "world"}, status_code=HTTP_200_OK, media_type=MediaType.JSON
            )
            await response(scope=scope, receive=receive, send=send)
        return
    response = Response(
        {"detail": "unsupported request"},
        status_code=HTTP_400_BAD_REQUEST,
        media_type=MediaType.JSON,
    )
    await response(scope=scope, receive=receive, send=send)
```

## Limitations of ASGI route handlers

In difference to the other route handlers, the `asgi` route handler accepts only 3 kwargs that **must** be defined:

- `scope`, a mapping of values describing the ASGI connection. It always includes a `type` key, with the values being
  either `http` or `websocket`, and a `path` key. If the type is `http`, the scope dictionary will also include
  a `method` key with the value being one of `DELETE, GET, POST, PATCH, PUT, HEAD`.
- `receive`, an injected function by which the ASGI application receives messages.
- `send`, an injected function by which the ASGI application sends messages.

You can read more about these in the [ASGI specification](https://asgi.readthedocs.io/en/latest/specs/main.html).

Additionally, ASGI route handler functions **must** be async functions. This is enforced using inspection, and if the
function is not an async function, an informative exception will be raised.

## ASGI Route Handler Kwargs

Aside from `path`, the `asgi` route handler accepts the following optional kwargs:

- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions.
  See [exception-handlers](../17-exceptions#exception-handling).
- `guards`: A list of [guards](../9-guards.md).
- `name`: A unique name that identifies the route handler. See: [route handler indexing](4-route-handler-indexing.md).
- `opt`: String keyed dictionary of arbitrary value that can be used by [guards](../9-guards.md).
