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

The `starlite.router.Router` constructor also accepts the following kwargs:

- `after_request`: A [after request lifecycle hook handler](../13-lifecycle-hooks.md#after-request).
- `after_response`: A [after response lifecycle hook handler](../13-lifecycle-hooks.md#after-response).
- `before_request`: A [before request lifecycle hook handler](../13-lifecycle-hooks.md#before-request).
- `dependencies`: A dictionary mapping dependency providers. See [dependency-injection](../6-dependency-injection/0-dependency-injection-intro.md).
- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions. See [exception-handlers](../17-exceptions#exception-handling).
- `guards`: A list of guard callable. See [guards](../9-guards.md).
- `middleware`: A list of middlewares. See [middleware](../7-middleware.md).
- `parameters`: A mapping of parameters definition that will be available on all sub route handlers. See [layered parameters](../3-parameters/4-layered-parameters.md).
- `response_class`: A custom response class to be used as the app's default. See [using-custom-responses](../5-responses.md#using-custom-responses).
- `response_headers`: A dictionary of `ResponseHeader` instances. See [response-headers](../5-responses.md#response-headers).
- `tags`: A list of tags to add to the openapi path definitions defined on the router. See [open-api](../12-openapi.md).
