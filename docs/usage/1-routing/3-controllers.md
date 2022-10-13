# Controllers

Controllers are subclasses of the class `starlite.controller.Controller`. They are used to organize endpoints under a
specific sub-path, which is the controller's path. Their purpose is to allow users to utilize python OOP for better code
organization and organize code by logical concerns.

```python
from pydantic import BaseModel, UUID4
from starlite.controller import Controller
from starlite.handlers import get, post, patch, delete
from starlite.types import Partial


class UserOrder(BaseModel):
    user_id: int
    order: str


class UserOrderController(Controller):
    path = "/user-order"

    @post()
    async def create_user_order(self, data: UserOrder) -> UserOrder:
        ...

    @get(path="/{order_id:uuid}")
    async def retrieve_user_order(self, order_id: UUID4) -> UserOrder:
        ...

    @patch(path="/{order_id:uuid}")
    async def update_user_order(
        self, order_id: UUID4, data: Partial[UserOrder]
    ) -> UserOrder:
        ...

    @delete(path="/{order_id:uuid}")
    async def delete_user_order(self, order_id: UUID4) -> None:
        ...
```

The above is a simple example of a "CRUD" controller for a model called `UserOrder`. You can place as
many [route handler methods](../2-route-handlers/1-http-route-handlers.md) on a controller,
as long as the combination of path+http method is unique.

The `path` that is defined on the Controller is appended before the path that is defined for the route handlers declared
on it. Thus, in the above example, `create_user_order` has the path of the controller - `/user-order/`,
while `retrieve_user_order` has the path `/user-order/{order_id:uuid}"`.

!!! note
    If you do not declare a `path` class variable on the controller, it will default to the root path of "/".

See the [API Reference][starlite.controller.Controller] for full details on the Controller class and the kwargs it accepts.
