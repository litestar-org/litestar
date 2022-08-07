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
    async def delete_user_order(self, order_id: UUID4) -> UserOrder:
        ...
```

The above is a simple example of a "CRUD" controller for a model called `UserOrder`. You can place as
many [route handler methods](../2-route-handlers/1_http_route_handlers.md) on a controller,
as long as the combination of path+http method is unique.

The `path` that is defined on the Controller is appended before the path that is defined for the route handlers declared
on it. Thus, in the above example, `create_user_order` has the path of the controller - `/user-order/`,
while `retrieve_user_order` has the path `/user-order/{order_id:uuid}"`.

<!-- prettier-ignore -->
!!! note
    If you do not declare a `path` class variable on the controller, it will default to the root path of "/".

Aside from the `path` class variable see above, you can also define the following class variables:

- `after_request`: A [after request lifecycle hook handler](../13-lifecycle-hooks.md#after-request).
- `after_response`: A [after response lifecycle hook handler](../13-lifecycle-hooks.md#after-response).
- `before_request`: A [before request lifecycle hook handler](../13-lifecycle-hooks.md#before-request).
- `dependencies`: A dictionary mapping dependency providers. See [dependency-injection](../6-dependency-injection/0-dependency-injection-intro.md).
- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions. See [exception-handlers](../17-exceptions#exception-handling).
- `guards`: A list of guard callable. See [guards](../9-guards.md).
- `middleware`: A list of middlewares. See [middleware](../7-middleware.md).
- `parameters`: A mapping of parameters definition that will be available on all sub route handlers. See [layered parameters](../3-parameters/4-layered-parameters.md).
- `response_class`: A custom response class to be used as the app's default. See [using-custom-responses](../5-responses/0-responses-intro.md#using-custom-responses).
- `response_headers`: A dictionary of `ResponseHeader` instances. See [response-headers](../5-responses/0-responses-intro.md#response-headers).
- `tags`: A list of tags to add to the openapi path definitions defined on the router. See [open-api](../12-openapi.md).
