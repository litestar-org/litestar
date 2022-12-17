# Using Application State

As seen in the examples for the [on_startup / on_shutdown hooks](1-startup-and-shutdown.md), callables passed to these
hooks can receive an optional kwarg called `state`, which is the application's state object.

The advantage of using application `state`, is that it can be accessed during multiple stages of the connection, and
it can be injected into dependencies and route handlers.

The Application State is an instance of the [`State`][starlite.datastructures.State] datastructure, and it is accessible
via the
[`app.state`][starlite.app.Starlite] attribute. As such it can be accessed wherever the app instance is accessible.

It's important to understand in this context that the application instance is injected into the ASGI `scope` mapping for
each connection (i.e. request or websocket connection) as `scope["app"].state`. This makes the application accessible
wherever the scope mapping is available, e.g. in middleware, on [`Request`][starlite.connection.Request] and
[`Websocket`][starlite.connection.WebSocket] instances (accessible as `request.app` / `socket.app`) and many other
places.

Therefore, state offers an easy way to share contextual data between disparate parts of the application, as seen below:

```py title="Using Application State"
--8<-- "examples/application_state/using_application_state.py"
```

## Initializing Application State

You can pass an object from which the application state will be instantiated using the `initial_state` kwarg of the
Starlite constructor:

```py title="Using Application State"
--8<-- "examples/application_state/passing_initial_state.py"
```

!!! note
    The `initial_state` can be a dictionary, an instance of [`ImmutableState`][starlite.datastructures.ImmutableState]
    or [`State`][starlite.datastructures.State], or a list of tuples containing key/value pairs.

!!! important
    Any value passed to `initial_state` will be deep copied - to prevent mutation from outside the application context.

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



While this is very powerful, it might encourage users to follow anti-patterns: it's important to emphasize that using
state can lead to code that's hard to reason about and bugs that are difficult to understand, due to changes in
different ASGI contexts. As such, this pattern should be used only when it is the best choice and in a limited fashion.
To discourage its use, Starlite also offers a builtin `ImmutableState` class. You can use this class to type state and
ensure that no mutation of state is allowed:

```py title="Using Custom State"
--8<-- "examples/application_state/using_immutable_state.py"
```
