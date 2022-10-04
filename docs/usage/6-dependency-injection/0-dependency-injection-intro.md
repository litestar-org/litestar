# Dependency Injection

Starlite has a simple but powerful dependency injection system that allows for declaring dependencies on all layers of
the application:

```python
from starlite import Controller, Router, Starlite, Provide, get


def bool_fn() -> bool:
    ...


def dict_fn() -> dict:
    ...


def list_fn() -> list:
    ...


def int_fn() -> int:
    ...


class MyController(Controller):
    path = "/controller"
    # on the controller
    dependencies = {"controller_dependency": Provide(list_fn)}

    # on the route handler
    @get(path="/handler", dependencies={"local_dependency": Provide(int_fn)})
    def my_route_handler(
        self,
        app_dependency: bool,
        router_dependency: dict,
        controller_dependency: list,
        local_dependency: int,
    ) -> None:
        ...

    # on the router


my_router = Router(
    path="/router",
    dependencies={"router_dependency": Provide(dict_fn)},
    route_handlers=[MyController],
)

# on the app
app = Starlite(
    route_handlers=[my_router], dependencies={"app_dependency": Provide(bool_fn)}
)
```

The above example illustrates how dependencies are declared on the different layers of the application.

Dependencies are callables - sync or async functions, methods or class instances that implement the `__call__` method -
that are wrapped inside an instance of the `starlite.datastructures.Provide` class.

## Pre-requisites and Scope

The pre-requisites for dependency injection are these:

1. dependencies must be callables.
2. dependencies can receive kwargs and a `self` arg but not positional args.
3. the kwarg name and the dependency key must be identical.
4. the dependency must be declared using the `Provide` class.
5. the dependency must be in the _scope_ of the handler function.

What is _scope_ in this context? Dependencies are **isolated** to the context in which they are declared. Thus, in the
above example, the `local_dependency` can only be accessed within the specific route handler on which it was declared;
The `controller_dependency` is available only for route handlers on that specific controller; And the router
dependencies are available only to the route handlers registered on that particular router. Only the `app_dependencies`
are available to all route handlers.
