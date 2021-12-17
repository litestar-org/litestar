# StarLite

Starlite is a simple, flexible and extensible ASGI API framework built on top of Starlette and Pydantic. It was inspired
by FastAPI and NestJS.

## Example: Controller Pattern

Starlite supports class API components called "Controllers". Controllers are meant to group logical subcomponents, for
example - consider the following `UserController`:

```python3
from pydantic import BaseModel, UUID4
from starlite import Starlite
from starlite.controller import Controller
from starlite.handlers import get, post, put, patch, delete
from starlite.types import Partial


class User(BaseModel):
    first_name: str
    last_name: str
    id: UUID4


class UserController(Controller):
    path = "/users"

    @post()
    async def create(self, data: User) -> User:
        ...

    @get()
    async def get_users(self) -> list[User]:
        ...

    @patch()
    async def partial_update_user(self, data: Partial[User]) -> User:
        ...

    @put()
    async def bulk_update_users(self, data: list[User]) -> list[User]:
        ...

    @get(path="/{user_id}")
    async def get_user_by_id(self, user_id: UUID4) -> User:
        ...

    @delete(path="/{user_id}")
    async def delete_user_by_id(self, user_id: UUID4) -> User:
        ...


app = Starlite(route_handlers=[UserController])

```

You can also use standalone functions:

## Example: Controller Pattern

Starlite supports class API components called "Controllers". Controllers are meant to group logical subcomponents, for
example - consider the following `UserController`:

```python3
from pydantic import BaseModel, UUID4
from starlite import Starlite
from starlite.handlers import get, post, put, patch, delete
from starlite.types import Partial


class User(BaseModel):
    first_name: str
    last_name: str
    id: UUID4


@post(path="/users")
async def create(self, data: User) -> User:
    ...


@get(path="/users")
async def get_users(self) -> list[User]:
    ...


@patch(path="/users")
async def partial_update_user(self, data: Partial[User]) -> User:
    ...


@put(path="/users")
async def bulk_update_users(self, data: list[User]) -> list[User]:
    ...


@get(path="/users/{user_id}")
async def get_user_by_id(self, user_id: UUID4) -> User:
    ...


@delete(path="/users/{user_id}")
async def delete_user_by_id(self, user_id: UUID4) -> User:
    ...


app = Starlite(
    route_handlers=[create, get_users, partial_update_user, bulk_update_users, get_user_by_id, delete_user_by_id])

```

Routers:

```python3
from pydantic import BaseModel, UUID4
from starlite import Starlite, Controller, Router, post


class User(BaseModel):
    first_name: str
    last_name: str
    id: UUID4

class RegularUsersController(Controller):
    path = "/regular"

    @post(path="/xyz/{my_param}/")
    async def create(self, data: User) -> User:
        ...


class SpecialUsersController(Controller):
    path = "/regular"

    @post(path="/xyz/{my_param}/")
    async def create(self, data: User) -> User:
        ...

sub_router = Router(path="/sub", route_handlers=[SpecialUsersController])

user_router = Router(path="/users", path_handler=[RegularUsersController, sub_router])


app = Starlite(
    route_handlers=[user_router])
)
```

Dependency Injection:

```python3
from pydantic import BaseModel, UUID4
from starlite import Starlite, Controller, Router, post, Provide


class User(BaseModel):
    first_name: str
    last_name: str
    id: UUID4

class RegularUsersController(Controller):
    path = "/regular"

    @post(path="/xyz/{my_param}/")
    async def create(self, data: User) -> User:
        ...


class SpecialUsersController(Controller):
    path = "/regular"

    @post(path="/xyz/{my_param}/")
    async def create(self, data: User) -> User:
        ...

sub_router = Router(path="/sub", route_handlers=[SpecialUsersController])

user_router = Router(path="/users", path_handler=[RegularUsersController, sub_router])


def my_dependency(headers: Dict[str, str])

app = Starlite(
    route_handlers=[user_router],
    dependencies={
        "first": Provide()
    }
)
```
