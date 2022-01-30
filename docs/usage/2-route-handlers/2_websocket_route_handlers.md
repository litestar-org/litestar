# Websocket Route Handlers

<!-- prettier-ignore -->
!!! info
    This feature is available from v0.2.0 onwards

Alongside the HTTP Route handlers discussed above, Starlite also support Websockets via the `websocket` decorator:

```python
from starlite import WebSocket, websocket


@websocket(path="/socket")
async def my_websocket_handler(socket: WebSocket) -> None:
    await socket.accept()
    await socket.send_json({...})
    await socket.close()
```

The `websocket` decorator is also an aliased class, in this case - of the `WebsocketRouteHandler`. Thus. you can write
the above like so:

```python
from starlite import WebSocket, WebsocketRouteHandler


@WebsocketRouteHandler(path="/socket")
async def my_websocket_handler(socket: WebSocket) -> None:
    await socket.accept()
    await socket.send_json({...})
    await socket.close()
```

In difference to HTTP routes handlers, websocket handlers have the following requirements:

1. they **must** declare a `socket` kwarg. If this is missing an exception will be raised.
2. they **must** have a return annotation of `None`. Any other annotation, or lack thereof, will raise an exception.

Additionally, they should be async because the socket interface is async - but this is not enforced. You will not be
able to do anything meaningful without this and python will raise errors as required.

In all other regards websocket handlers function exactly like other route handlers.

<!-- prettier-ignore -->
!!! note
    OpenAPI currently does not support websockets. As a result not schema will be generated for websocket route
    handlers, and you cannot configure any schema related parameters for these.
