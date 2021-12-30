# Guards

Guards are callables that receive two arguments - the request object and the route handler.

The guard should `authorize` the request, that is - check that the request is allowed to reach the endpoint handler in
question, if not - an HTTPException, usually a `NotAuthorizedException` with a `status_code` of 401, should be raised.

To illustrate this we will implement a rudimentary roles system in our Starlite app. As we have done
for [authentication](8-authentication.md) we will assume that we added some sort of persistence layer.

We begin by creating an `Enum` with two roles - `consumer` and `admin`:

```python title="my_app/enums.py"
from enum import Enum

class UserRole(str, Enum):
    CONSUMER = "consumer"
    ADMIN = "admin"
```

Our `User` model will now look like this:

```python title="my_app/models.py"
from pydantic import BaseModel, UUID4

from my_app.enums import UserRole


class User(BaseModel):
    id: UUID4
    role: UserRole

    @property
    def is_admin(self) -> bool:
        """Determines whether the user is an admin user"""
        return self.role == UserRole.ADMIN
```

Given that the User model now has a "role" property we can use it to authorize a request. Let's create a guard that only
allows admin users to access certain route handlers:

```python title="my_app/guards.py"
from starlite import Request, RouteHandler, NotAuthorizedException

from my_app.models import User


def admin_user_guard(request: Request[User], _: RouteHandler) -> None:
    if not request.user.is_admin:
        raise NotAuthorizedException()
```

We can now use it, for example - lets say we have a route handler that allows users to create users:

```python
from starlite import post

from my_app.guards import admin_user_guard
from my_app.models import User


@post(path="/user", guards=[admin_user_guard])
def create_user(data: User) -> User:
    ...
```

Thus, only an admin user would be able to post a user to `create_user`.

## Guard Scopes

Guards can be declared on all levels of the app - the app, routers, controllers and individual route handlers (functions
or methods):

```python
from starlite import Controller, Router, Starlite

from my_app.guards import admin_user_guard


# controller
class UserController(Controller):
    path = "/user"
    guards = [admin_user_guard]

    ...


# router
admin_router = Router(
    path="admin", route_handlers=[UserController], guards=[admin_user_guard]
)

# app

app = Starlite(route_handlers=[admin_router], guards=[admin_user_guard])
```

The deciding factor on where to place a guard is on the kind of access restriction that is necessary- do only specific
route handlers need to be restricted? an entire controller? all the paths under a specific router? or the entire app?

As you can see in the above examples - `guards` is a list. This means you can add **multiple** guards at every layer.
Unlike `dependencies`, guards do not override each other but are rather *cumulative*. This means that you can define guards on different levels of your app, and they will combine.

## The Route Handler "opt" Key

Occasionally there might be a need to set some values on the route handler itself - these can be permissions, or some other flag. To this end, all route handler decorators can receive the kwarg `opt` which adds a dictionary of any arbitrary values to the route handler. For example:

```python
from starlite import get


@get(path="/", opt={"permissions": [...]})
def my_route_handler() -> None:
    ...
```

To illustrate this lets say we want to have an endpoint that is guarded by "secret" token, to which end we create the following guard:

```python title="my_app/guards.py"
from starlite import Request, RouteHandler, NotAuthorizedException


def secret_token_guard(request: Request[User], route_handler: RouteHandler) -> None:
    if route_handler.opt.get("secret") and not request.headers.get("Secret-Header", "") == route_handler.opt["secret"]:
        raise NotAuthorizedException()
```

We can now use this in our endpoint of choice like so:

```python
from os import environ

from starlite import get

from my_app.guards import secret_token_guard


@get("/secret", guards=[secret_token_guard], opt={"secret": environ.get("SECRET")})
def secret_endpoint() -> None:
    ...
```
