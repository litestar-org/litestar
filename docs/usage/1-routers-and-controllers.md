# Routers and Controllers

In most cases an API is composed of multiple endpoints, often with different sub-paths. Starlite offers two class
components that make this simple to achieve - `Router` and `Controller`.

## Controllers

```python
# my_app/orders/controllers/user_order_controller.py
from pydantic import UUID4
from starlite.controller import Controller
from starlite.handlers import get, post, patch, delete
from starlite.types import Partial

from my_app.orders.models import UserOrder


class UserOrderController(Controller):
    path = "/user"

    @post()
    async def create_user_order(self, data: UserOrder) -> UserOrder:
        ...

    @get(path="/{order_id:uuid}")
    async def retrieve_user_order(self, order_id: UUID4) -> UserOrder:
        ...

    @patch(path="/{order_id:uuid}")
    async def update_user_order(self, order_id: UUID4, data: Partial[UserOrder]) -> UserOrder:
        ...

    @delete(path="/{order_id:uuid}")
    async def delete_user_order(self, order_id: UUID4) -> UserOrder:
        ...
```

Controllers are subclasses of the Starlite `Controller` class that are used to logically organize endpoints. You can
place as many [route handler](2-route-handlers.md) methods on a controller, as long as the combination of path+http
method is unique.

The `path` that is defined on the Controller is appended before whatever path is defined for the route handlers on it.
Thus, in the above example, `create_user_order` has the path of the controller, while `retrieve_user_order` has the
path `/user/{order_id:uuid}"`.

Aside from the `path` class variable, which **must** be set, you can also set the following optional class variables:

* `dependencies`: a list of `Provide` classes that will be available as injectable dependencies for all methods defined
  on the controller. See [dependency-injection](5-dependency-injection.md) for more details.
* `response_headers`: a dictionary of `ResponseHeader` instances that will be set for all methods defined on the
  controller. See [response headers](4-responses.md).

## Routers

```python
# my_app/order/router.py
from starlite import Router

from my_app.order.controllers import UserOrderController, PartnerOrderController

order_router = Router(path="/orders", route_handlers=[UserOrderController, PartnerOrderController])
```

The Starlite `Router` class is used to organize sub-paths under a common namespace. In the above, it registers two
different controllers, and each controller's respective path is combined with the router's path.

Assuming that the `UserOrderController` defines a _path_ of "/user" and `PartnerOrderController` defines a _path_ of "
/partner", their paths will be "/orders/user" and "order/partner" respectively.

Aside from `path` and `route_handlers` which are required kwargs, you can also pass the following kwargs to Router:

* `dependencies`: a list of `Provide` classes that will be available as injectable dependencies for all methods defined
  on the controller. See [dependency-injection](5-dependency-injection.md) for more details.
* `response_headers`: a dictionary of `ResponseHeader` instances that will be set for all methods defined on the
  controller. See [response headers](4-responses.md).
* `redirect_slashes`: enables or disables optional trailing slash, defaults to `True`.

## Registering Routes

At the root of every Starlite application there is an instance of Starlite, on which the root level controllers, routers
and/or router-handlers are registered, for example:

```python
from starlite import get, Starlite

from users import UserController
from orders import order_router


@get("/")
def health_check() -> str:
    return "healthy"


app = Starlite(route_handlers=[health_check, UserController, order_router])
```

You can combine Routers, Controllers and individual route handler functions as the need arises. You can also do the same
for routers - that is, you can register on a router exactly the same component that you can register on the Starlite
app.

Thus, you can also register other instance of `Router` on a router:

```python
# my_app/order/router.py
from starlite import Router

from my_app.order.controllers import UserOrderController, PartnerOrderController

order_router = Router(path="/orders", route_handlers=[UserOrderController, PartnerOrderController])

other_router = Router(path="/base", route_handlers=[order_router])
```

Once order_router is registered on `other_router`, the previously mentioned paths will now be: "/base/orders/user" and "
/base/order/partner" respectively. You can nest routers as you see fit - but be aware that once a router has been
registered it cannot be re-registered or an exception will be raised.

Finally, you should note that you can register a controller on different routers, the same way you can register
individual functions:

```python
# my_app/users/router.py
from starlite import Router

from my_app.user.controllers import UserController

internal_router = Router(path="/internal", route_handlers=[UserController])
partner_router = Router(path="/partner", route_handlers=[UserController])
consumer_router = Router(path="/consumer", route_handlers=[UserController])
```

In the above pattern the same `UserController` class has been registered on three different routers. Each router
instance will be available on a different sub-path, e.g. "/internal/users", "/partner/users" and "/consumer/users". This
is not a problem because the dependencies for each controller instance are isolated.
