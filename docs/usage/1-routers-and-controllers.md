# Routers and Controllers

In most cases an API is composed of multiple endpoints, often with different sub-paths. Starlite offers two class
components that make this simple to achieve - `Router` and `Controller`.

## Controllers

Controllers are subclasses of the Starlite `Controller` class that are used to organize endpoints under a specific
sub-path. You can place as many [route handler](2-route-handlers/1_http_route_handlers.md) methods on a controller, as long as the combination
of path+http method is unique. The distinct advantage of using controllers is that they allow both code sharing using
OOP techniques and make the code better organized by promoting concern based code splitting.

```python title="my_app/orders/controllers/user_order_controller.py"
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

The `path` that is defined on the Controller is appended before the path that is defined for the route handlers declared
on it. Thus, in the above example, `create_user_order` has the path of the controller, while `retrieve_user_order` has
the path `/user/{order_id:uuid}"`.

<!-- prettier-ignore -->
!!! note
    You do not have to declare a `path` variable, yet if the path variable is missing or is an empty string, it
    will default to the root path of "/".

Aside from the `path` class variable, you can also set the following optional class variables:

- `dependencies`: A dictionary mapping dependency providers. See [dependency-injection](6-dependency-injection.md).
- `guards`: A list of callables. See [guards](9-guards.md).
- `response_class`: A custom response class to be used as the app default.
  See [using-custom-responses](5-responses.md#using-custom-responses).
- `response_headers`: A dictionary of `ResponseHeader` instances.
  See [response-headers](5-responses.md#response-headers).
- `before_request`: a sync or async function to execute before a `Request` is passed to a route handler (method) on the
  controller. If this function returns a value, the request will not reach the route handler, and instead this value
  will be used.
- `after_request`: a sync or async function to execute before the `Response` is returned. This function receives the
  `Respose` object and it must return a `Response` object.
- `tags`: a list of `str`, which correlate to the [tag specification](https://spec.openapis.org/oas/latest.html#tag-object).
- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions.
  See [exception-handlers](0-the-starlite-app#exception-handling).

## Routers

```python title="my_app/order/router.py"
from starlite import Router

from my_app.order.controllers import UserOrderController, PartnerOrderController

order_router = Router(path="/orders", route_handlers=[UserOrderController, PartnerOrderController])
```

The Starlite `Router` class is used to organize sub-paths under a common namespace. In the above, it registers two
different controllers, and each controller's respective path is combined with the router's path.

Assuming that the `UserOrderController` defines a _path_ of "/user" and `PartnerOrderController` defines a _path_ of "
/partner", their paths will be "/orders/user" and "orders/partner" respectively.

Aside from `path` and `route_handlers` which are required kwargs, you can also pass the following kwargs to Router:

- `dependencies`: A dictionary mapping dependency providers. See [dependency-injection](6-dependency-injection.md).
- `guards`: A list of callables. See [guards](9-guards.md).
- `response_class`: A custom response class to be used as the app default.
  See [using-custom-responses](5-responses.md#using-custom-responses).
- `response_headers`: A dictionary of `ResponseHeader` instances.
  See [response-headers](5-responses.md#response-headers).
- `before_request`: a sync or async function to execute before a `Request` is passed to a route handler (function or
  controller method) on the router. If this function returns a value, the request will not reach the route handler,
  and instead this value will be used.
- `after_request`: a sync or async function to execute before the `Response` is returned. This function receives the
  `Respose` object and it must return a `Response` object.
- `tags`: a list of `str`, which correlate to the [tag specification](https://spec.openapis.org/oas/latest.html#tag-object).
- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions.
  See [exception-handlers](0-the-starlite-app#exception-handling).

## Registering Routes

At the root of every Starlite application there is an instance of Starlite, on which the root level controllers, routers
and/or router-handlers are registered, for example:

```python title="my_app/main.py"
from starlite import get, Starlite

from users import UserController
from orders import order_router


@get(path="/")
def health_check() -> str:
    return "healthy"


app = Starlite(route_handlers=[health_check, UserController, order_router])
```

The root level components registered on the app have whatever path is defined on them without anything appended to it.
Thus, the `health_check` function above is available on "/" and the methods of `UserController` are available on "
/users".

To handle more complex path schemas you should use routers, which can register Controllers, individual functions but
also other routers:

```python title="my_app/order/router.py"
from starlite import Router

from my_app.order.controllers import UserOrderController, PartnerOrderController

order_router = Router(path="/orders", route_handlers=[UserOrderController, PartnerOrderController])

base_router = Router(path="/base", route_handlers=[order_router])
```

Once `order_router` is registered on `base_router`, the controllers registered on it will be respectively available
on: "/base/orders/user" and "/base/order/partner" respectively.

<!-- prettier-ignore -->
!!! important
    You can nest routers as you see fit - but be aware that once a router has been registered it cannot be
    re-registered or an exception will be raised.

### Registering Controllers Multiple Times

Unlike routers, which can only be registered once, the same controller can be registered on different routers:

```python title="my_app/users/router.py"
from starlite import Router

from my_app.user.controllers import UserController

internal_router = Router(path="/internal", route_handlers=[UserController])
partner_router = Router(path="/partner", route_handlers=[UserController])
consumer_router = Router(path="/consumer", route_handlers=[UserController])
```

In the above, the same `UserController` class has been registered on three different routers. This is possible because
what is passed to the router is not a class instance but rather the class itself. The router creates its own instance of
the controller, which ensures encapsulation.

Therefore , in the above example, three different instance of `UserController` will be created, each mounted on a
different sub-path, e.g. "/internal/users", "/partner/users"
and "/consumer/users".

### Registering Standalone Route Handlers Multiple Times

You can also register standalone route handler handlers multiple times:

```python title="my_app/users/router.py"
from starlite import Router, get


@get(path="/handler")
def my_route_handler() -> None:
  ...

internal_router = Router(path="/internal", route_handlers=[my_route_handler])
partner_router = Router(path="/partner", route_handlers=[my_route_handler])
consumer_router = Router(path="/consumer", route_handlers=[my_route_handler])
```

This is possible because the route handler is copied when registered. Thus, each router has its own unique instance of
the route handler rather than the same one. Path behaviour is identical to controllers, namely, the route handler
function will be accessible in the following paths: "/internal/handler", "/partner/handler" and "/consumer/handler".

## Relation to Starlette Routing

Although Starlite uses the Starlette ASGI toolkit, Starlite does not extend or use the Starlette routing system as is.
That is to say, the Starlite `HTTPRoute`, `WebSocketRoute` and `Router` classes do not extend their Starlette
equivalents, but are rather independent implementations.

It's important to note the following:

1. Starlite Routers have a smaller api surface and do not expose decorators.
2. Starlite Routers and Routes are not standalone ASGI apps and always depend upon a Starlite app instance.
3. Starlite enforces a simple routing structure and doesn't support multiple-hosts and complex mounts.

The reason for this decision is to enforce a **simple** routing pattern. It's true that this eliminates certain
possibilities, for example - you cannot re-use paths based on different "Host" headers, as you can in Starlette, but
this is intentional and is meant to enforce best practices.
