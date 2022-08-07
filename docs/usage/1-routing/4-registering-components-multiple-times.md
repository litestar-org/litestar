# Registering Components Multiple Times

You can register both standalone route handler functions and controllers multiple time.

## Registering Controllers Multiple Times

```python
from starlite import Router, Controller, get


class MyController(Controller):
    path = "/controller"

    @get()
    def handler(self) -> None:
        ...


internal_router = Router(path="/internal", route_handlers=[MyController])
partner_router = Router(path="/partner", route_handlers=[MyController])
consumer_router = Router(path="/consumer", route_handlers=[MyController])
```

In the above, the same `MyController` class has been registered on three different routers. This is possible because
what is passed to the router is not a class instance but rather the class itself. The router creates its own instance of
the controller, which ensures encapsulation.

Therefore , in the above example, three different instances of `MyController` will be created, each mounted on a
different sub-path, e.g. `/internal/controller`, `/partner/controller` and `/consumer/controller`.

## Registering Standalone Route Handlers Multiple Times

You can also register standalone route handlers multiple times:

```python
from starlite import Starlite, Router, get


@get(path="/handler")
def my_route_handler() -> None:
    ...


internal_router = Router(path="/internal", route_handlers=[my_route_handler])
partner_router = Router(path="/partner", route_handlers=[my_route_handler])
consumer_router = Router(path="/consumer", route_handlers=[my_route_handler])

Starlite(route_handlers=[internal_router, partner_router, consumer_router])
```

When the handler function is registered, it's actually copied. Thus, each router has its own unique instance of
the route handler. Path behaviour is identical to that of controllers above, namely, the route handler
function will be accessible in the following paths: `/internal/handler`, `/partner/handler` and `/consumer/handler`.

<!-- prettier-ignore -->
!!! important
    You can nest routers as you see fit - but be aware that once a router has been registered it cannot be
    re-registered or an exception will be raised.
