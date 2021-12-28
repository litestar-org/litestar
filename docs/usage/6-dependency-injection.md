# Dependency Injection

Starlite has a simple but powerful dependency injection system. To explain how it works lets begin with 4 different
functions, each returning a different kind of value:

```python
def bool_fn() -> bool:
    ...


def dict_fn() -> dict:
    ...


def list_fn() -> list:
    ...


def int_fn() -> int:
    ...
```

We can declare dependencies on different levels of the application using the `Provide` class:

```python
from starlite import Controller, Router, Starlite, Provide, get

from my_app.dependencies import bool_fn, dict_fn, int_fn, list_fn


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

In the above example, the route handler function `my_route_handler` has four different dependencies injected into it as
kwargs.

## DI Pre-requisites and Scope

The pre-requisites for dependency injection are these:

1. dependencies must be callables (sync or async functions or methods).
2. dependencies can receive kwargs and a `self` arg but not other args.
3. the kwarg name and the dependency key must be identical.
4. the dependency must be declared using the `Provide` class.
5. the dependency must be in the _scope_ of the handler function.

What is _scope_ in this context? Dependencies are **isolated** to the context in which they are declared. Thus, in the
above example, the `local_dependency` can only be accessed within the specific router handler for which it was declared;
The `controller_dependency` is available only for route handlers on that specific controller; And the router
dependencies are available only to the route handlers registered on that particular router. Only the `app_dependencies`
are available to all route handlers.

## Dependency Kwargs

As stated above dependencies can receive kwargs but no args. The reason for this is that dependencies are parsed using
the same mechanism that parses route handler functions, and they too - like route handler functions, can have data
injected into them.

In fact, you can inject the same data that you
can [inject into route handlers](2-route-handlers.md#handler-function-kwargs) except other dependencies.

For example, lets say we have a dependency to authenticate the user:

```python title="my_app/dependencies.py"
from starlite import NotAuthorizedException, Parameter
from pydantic import UUID4

from my_app.models import User

async def authenticate_user(
    user_id: UUID4, # path parameter
    bearer_token: Parameter(header="Authorization"),  # header parameter
    raises=[NotAuthorizedException]
) -> User:
    ...
```

As you can see above, the authenticate_user method is in effect expecting a path parameter called `user_id` and a header
parameter called `bearer_token` to be injected to it from the request. This means that whatever function or method is
going to use this must declare this path parameter in its path.

Thus, our `UserController` has a method that does exactly that:

```python title="my_app/user/controller.py
from starlite import Controller, get

from my_app.models import User


class UserController(Controller):
    path = "/user"

    @get("/{user_id:uuid}")
    def retrieve_user(self, user: User) -> User
        return user
```

Because we want user to be accessible in multiple controllers throughout the app, we decided to register it on the app
level:

```python title="my_app/main.py"
from starlite import Starlite, Provide

from my_app.dependencies import authenticate_user
from my_app.user import UserController

app = Starlite(route_handlers=[UserController], dependencies={"user": Provide(authenticate_user)})
```

If we just wanted user to be accessible for the methods of the `UserController` or even just the `retrieve_user` method
we could have instead registered it on a lower scope.

## Overriding Dependencies

Because dependencies are declared at each level using a string keyed dictionary, overriding dependencies is very simple:

```python
from starlite import Controller, Provide, get

from my_app.dependencies import bool_fn, dict_fn


class MyController(Controller):
    path = "/controller"
    # on the controller
    dependencies = {"some_dependency": Provide(dict_fn)}

    # on the route handler
    @get(path="/handler", dependencies={"some_dependency": Provide(bool_fn)})
    def my_route_handler(
        self,
        some_dependency: bool,
    ) -> None:
        ...
```

As you can see in the above - the lower scoped route handler function declares a dependency with the same key as the one
declared on the higher scoped controller. The lowest scoped dependency therefore overrides the higher scoped one. This
logic applies on all layers.

## The Provide Class

Provide is a simple wrapper around the callable. You can pass to it a single kwarg - `use_cache`. By default `Provide`
will not cache the return value of the dependency, that is - it will execute it on every call. If `use_cache` is used it
will cache the return value on the first execution and will not call it again - there is no sophisticated comparison on
kwargs or other elements happening, so you should be careful when you choose to use this option. Whats the use case for
this? If you have a dependency that should either not be called multiple times, or which has a constant return value
then this is useful.
