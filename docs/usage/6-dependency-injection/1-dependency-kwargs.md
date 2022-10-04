# Dependency Kwargs

As stated above dependencies can receive kwargs but no args. The reason for this is that dependencies are parsed using
the same mechanism that parses route handler functions, and they too - like route handler functions, can have data
injected into them.

In fact, you can inject the same data that you
can [inject into route handlers](../2-route-handlers/1-http-route-handlers.md#http-route-handlers-kwargs).

```python
from starlite import Controller, Provide, patch
from starlite.types.partial import Partial
from pydantic import BaseModel, UUID4


class User(BaseModel):
    id: UUID4
    name: str


async def retrieve_db_user(user_id: UUID4) -> User:
    ...


class UserController(Controller):
    path = "/user"
    dependencies = {"user": Provide(retrieve_db_user)}

    @patch(path="/{user_id:uuid}")
    async def update_user(self, data: Partial[User], user: User) -> User:
        ...
```

In the above example we have a `User` model that we are persisting into a db. The model is fetched using the helper
method `retrieve_db_user` which receives a `user_id` kwarg and retrieves the corresponding `User` instance.
The `UserController` class maps the `retrieve_db_user` provider to the key `user` in its `dependencies` dictionary. This
in turn makes it available as a kwarg in the `update_user` method.
