# Using Application State

As seen in the examples for the [on_startup / on_shutdown hooks](1-startup-and-shutdown.md), callables passed to these
hooks can receive an optional kwarg called `state`, which is the application's state object.

The advantage of using application `state`, is that it can be accessed during multiple stages of the connection, and
it can be injected into dependencies and route handlers.

The Application State is an instance of [`State`][starlite.datastructures.State]. It is accessible via the
[app state][starlite.app.Starlite], and it can be accessed via any application reference, such as:

- `starlite.connection.ASGIConnection.app.state` (accessible inside middleware - see the example below).
- [`ASGIConnection.app`][starlite.connection.ASGIConnection]
- [`Request.app`][starlite.connection.Request]
- [`Websocket.app`][starlite.connection.WebSocket]

The following complete example demonstrates different patterns of accessing Application State:

```py title="Using Application State"
--8<-- "examples/using_application_state.py"
```

Also, see [handler function kwargs](../2-route-handlers/1-http-route-handlers.md#http-route-handlers-kwargs).
