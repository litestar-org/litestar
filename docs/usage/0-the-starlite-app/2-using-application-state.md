# Using Application State

As seen in the examples for the [on_startup / on_shutdown hooks](1-startup-and-shutdown.md), callables passed to these
hooks can receive an optional kwarg called`state`, which is the application's state object.

This is the same object that is available on the Starlite instance as `.state` and it's an instance of the class
`starlite.datastructures.State`, which inherits from `starlette.datastructures.State`. Additionally, the application
state is accessible as `.app.state` on the `starlette.requests.HTTPConnection` object accessible to middleware, as well
as on the `starlite.connection.Request` and `starlite.connection.WebSocket` objects.

The advantage of using application `state`, is that it can be accessed during multiple stages of the connection, and
it can be injected into dependencies and route handlers as well, e.g. as follows:

```python
from starlite import State, get


@get("/some-path")
def my_handler(state: State) -> None:
    # application state is injected
    ...
```

or

```python
from starlite import State, Provide, get


def my_dependency(state: State) -> None:
    # application state is injected
    ...


@get("/some-path")
def my_handler(dep: Provide(my_dependency)) -> None:
    ...
```

See [handler function kwargs](../2-route-handlers/1_http_route_handlers.md#http-route-handlers-kwargs).
