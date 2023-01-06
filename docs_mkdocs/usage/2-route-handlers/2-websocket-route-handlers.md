# Websocket Route Handlers

Starlite supports Websockets via the [`websocket`][starlite.handlers.websocket] decorator:

```python
from starlite import WebSocket, websocket


@websocket(path="/socket")
async def my_websocket_handler(socket: WebSocket) -> None:
    await socket.accept()
    await socket.send_json({...})
    await socket.close()
```

The`websocket` decorator is an alias of the class
[`WebsocketRouteHandler`][starlite.handlers.websocket.WebsocketRouteHandler]. Thus, the below
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

!!! note
    OpenAPI currently does not support websockets. As such no schema will be generated for these route handlers.

See the [API Reference][starlite.handlers.WebsocketRouteHandler] for full details on the `websocket` decorator and the kwargs it accepts.
