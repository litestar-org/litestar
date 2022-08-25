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

These requirements are enforced using inspection, and if any of them is unfulfilled an informative exception will be raised.

<!-- prettier-ignore -->
!!! note
    OpenAPI currently does not support websockets. As such no schema will be generated for these route handlers.

## Websocket Route Handler Kwargs

Aside from `path`, the `asgi` route handler accepts the following optional kwargs:

- `dependencies`: A dictionary mapping dependency providers. See [dependency-injection](../6-dependency-injection/0-dependency-injection-intro.md).
- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions.
  See [exception-handlers](../17-exceptions#exception-handling).
- `guards`: A list of [guards](../9-guards.md).
- `middleware`: A list of [middlewares](../7-middleware/0-middleware-intro.md).
- `name`: A unique name that identifies the route handler. See: [route handler indexing](4-route-handler-indexing.md).
- `opt`: String keyed dictionary of arbitrary value that can be used by [guards](../9-guards.md).
