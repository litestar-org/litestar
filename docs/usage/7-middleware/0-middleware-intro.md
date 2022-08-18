# Middlewares

Middlewares in Starlite are ASGI apps that are called "in the middle" between the beginning of the request and the route
handler function.

## Using Middleware

<!-- prettier-ignore -->
!!! important
    Starlite allows users to use [Starlette Middleware](https://www.starlette.io/middleware/) and any 3rd
    party middlewares created for it, while offering its own middleware protocol as well.

## Layering Middleware

Starlite following its layered architecture also in middleware - allowing users to define middleware on all layers of
the application - the Starlite instance, routers, controllers and individual route handlers. For example:

```python
from starlite import Starlite, Controller, Router, get
from starlite.middleware.base import MiddlewareProtocol


class TopLayerMiddleware(MiddlewareProtocol):
    ...


class RouterLayerMiddleware(MiddlewareProtocol):
    ...


class ControllerLayerMiddleware(MiddlewareProtocol):
    ...


class RouteHandlerLayerMiddleware(MiddlewareProtocol):
    ...


class MyController(Controller):
    path = "/controller"
    middleware = [ControllerLayerMiddleware]

    @get("/handler", middleware=[RouteHandlerLayerMiddleware])
    def my_route_handlers(self) -> dict[str, str]:
        return {"hello": "world"}


router = Router(path="/router", middleware=[RouterLayerMiddleware])

app = Starlite(route_handlers=[router], middleware=[TopLayerMiddleware])
```

In the above example a request to "/router/controller/handler" will be processed by `TopLayerMiddleware`
-> `RouterLayerMiddleware` -> `ControllerLayerMiddleware` -> `RouteHandlerLayerMiddleware`. If multiple middlewares were
declared in a layer, these middlewares would be processed in the order of the list. I.e. in the example
below, `TopLayerMiddleware1` receives the `scope`, `receive` and `send` first, and it either creates a response and
responds, or calls
`TopLayerMiddleware2`:

```python
from starlite import Starlite
from starlite.middleware.base import MiddlewareProtocol


class TopLayerMiddleware1(MiddlewareProtocol):
    ...


class TopLayerMiddleware2(MiddlewareProtocol):
    ...


app = Starlite(
    route_handlers=[...], middleware=[TopLayerMiddleware1, TopLayerMiddleware2]
)
```
