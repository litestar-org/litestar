# Using Application State

As seen in the examples for the [on_startup / on_shutdown hooks](1-startup-and-shutdown.md), callables passed to these
hooks can receive an optional kwarg called `state`, which is the application's state object.

The advantage of using application `state`, is that it can be accessed during multiple stages of the connection, and
it can be injected into dependencies and route handlers.

The Application State is an instance of [`State`][starlite.datastructures.State]. It is accessible via the
[`app.state`][starlite.app.Starlite] attribute. As such it can be accessed wherever the app instance is accessible.

It's important to understand in this context that the application instance is injected into the ASGI `scope` mapping for
each connection (i.e. request or websocket connection) as `scope["app"].state`. This makes the application accessible
wherever
the scope mapping is available, e.g. in middleware, on [`Request`][starlite.connection.Request] and
[`Websocket`][starlite.connection.WebSocket] instances (accessible as `request.app` / `socket.app`) and many other
places.

Therefore, state offers an easy way to share contextual data between disparate parts of the application, as seen below:

```py title="Using Application State"
--8<-- "examples/using_application_state.py"
```

## Injecting Application State into Route Handlers and Dependencies

As seen in the above example, Starlite offers an easy way to inject state into route handlers and dependencies - simply
by specifying `state` as a kwarg to the handler function. I.e., you can simply do this in handler function or dependency
to access the application state:

```python
from starlite import get, State


@get("/")
def handler(state: State) -> None:
    ...
```

When using this pattern you can specify the class to use for the state object. This type is not merely for type
checkers, rather Starlite will instantiate a new state instance based on the type you set there. This allows users to
use custom classes for State, e.g.:

```python
from starlite import get, State


class MyState(State):
    count: int = 0

    def increment(self) -> None:
        self.count *= 1


@get("/")
def handler(state: MyState) -> dict:
    state.increment()
    return state.dict()
```

While this is very powerful, it might encourage users to follow anti-patterns: its important to emphasize that using
state can lead to hard to reason about code as well difficult to understand bugs due to changes in different ASGI
contexts. As such, this pattern should be used only when it is the best choice and in a limited fashion. To discourage
its use, Starlite also offers a builtin `ImmutableState` class. You can use this class to type state and ensure that no
mutation of state is allowed:

```python
from starlite import get, ImmutableState


@get("/")
def handler(state: ImmutableState) -> None:
    state.my_attribute = 1  # raises AttributeError
```
