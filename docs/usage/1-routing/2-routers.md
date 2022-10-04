# Routers

Routers are instances of `starlite.router.Router`, which is the base class for the `Starlite` app itself. A router can
register Controllers, route handler functions and other routers, similarly to the Starlite constructor:

```python
from starlite import Starlite, Router, get


@get("/{order_id:int}")
def order_handler(order_id: int) -> None:
    ...


order_router = Router(path="/orders", route_handlers=[order_handler])
base_router = Router(path="/base", route_handlers=[order_router])
app = Starlite(route_handlers=[base_router])
```

Once `order_router` is registered on `base_router`, the handler function registered on `order_router` will
become available on `/base/orders/{order_id}`.

See the [API Reference][starlite.router.Router] for full details on the Router class and the kwargs it accepts.
