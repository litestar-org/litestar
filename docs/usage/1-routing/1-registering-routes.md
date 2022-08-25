# Registering Routes

At the root of every `Starlite` application there is an instance of the class `starlite.app.Starlite`, on which the root
level controllers, routers and route handler functions are registered using the `route_handlers` kwarg:

```python
from starlite import Starlite, get


@get("/sub-path")
def sub_path_handler() -> None:
    ...


@get()
def root_handler() -> None:
    ...


app = Starlite(route_handlers=[root_handler, sub_path_handler])
```

Components registered on the app are appended to the root path. Thus, the `root_handler` function will be called for the
path "/", whereas the `sub_path_handler` will be called for "/sub-path". You can also declare a function to handle
multiple paths, e.g.:

```python
from starlite import get, Starlite


@get(["/", "/sub-path"])
def handler() -> None:
    ...


app = Starlite(route_handlers=[handler])
```

To handle more complex path schemas you should use [routers](./2-routers.md) and [controller](./3-controllers.md)

## Dynamic Route Registration

Occasionally there is a need for dynamic route registration. Starlite supports this via the `.register` method exposed
by the Starlite app instance:

```python
from starlite import Starlite, get


@get()
def root_handler() -> None:
    ...


app = Starlite(route_handlers=[root_handler])


@get("/sub-path")
def sub_path_handler() -> None:
    ...


app.register(sub_path_handler)
```

Since the app instance is attached to all instances of `HTTPConnection`, `Request` and `WebSocket` objects, you can in
effect call the `.register` method inside route handler functions, middlewares and even injected dependencies. For example:

```python
from typing import Any
from starlite import Starlite, Request, get


@get("/some-path")
def route_handler(request: Request[Any, Any]) -> None:
    @get("/sub-path")
    def sub_path_handler() -> None:
        ...

    request.app.register(sub_path_handler)


app = Starlite(route_handlers=[route_handler])
```

In the above we dynamically created the sub-path_handler and registered it inside the `route_handler` function.

<!-- prettier-ignore -->
!!! warning
    Although Starlite exposes the `.register` method, it should not be abused. Dynamic route registration increases the
    application complexity and makes it harder to reason about the code. It should therefore be used only when
    absolutely required.
