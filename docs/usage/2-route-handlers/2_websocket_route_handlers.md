# Websocket Route Handlers

Starlite supports Websockets via the `websocket` decorator:

```python
from starlite import WebSocket, websocket


@websocket(path="/socket")
async def my_websocket_handler(socket: WebSocket) -> None:
    await socket.accept()
    await socket.send_json({...})
    await socket.close()
```

The`websocket` decorator is an alias of the class `starlite.handlers.websocket.WebsocketRouteHandler`. Thus, the below
code is equivalent to the one above:

```python
from starlite import WebSocket, WebsocketRouteHandler


@WebsocketRouteHandler(path="/socket")
async def my_websocket_handler(socket: WebSocket) -> None:
    await socket.accept()
    await socket.send_json({...})
    await socket.close()
```

In difference to HTTP routes handlers, websocket handlers have the following requirements:

1. they **must** declare a `socket` kwarg.
2. they **must** have a return annotation of `None`.
3. they **must** be async functions.

These requirements are enforced using inspection, and if any of them is unfulfilled an informative
`ImproperlyConfiguredException` will be raised.

<!-- prettier-ignore -->
!!! note
    OpenAPI currently does not support websockets. As such no schema will be generated for these route handlers.

## ASGI Route Handler Kwargs

Aside from `path`, the `asgi` route handler accepts the following optional kwargs:

- `dependencies`: A dictionary mapping dependency providers. See [dependency-injection](../6-dependency-injection.md).
- `guards`: A list of [guards](../9-guards.md).
- `opt`: String keyed dictionary of arbitrary value that can be used by [guards](../9-guards.md).
