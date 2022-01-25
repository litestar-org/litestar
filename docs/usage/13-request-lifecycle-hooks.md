# Request Life Cycle Hooks

Starlite borrows the concept of `before_request` and `after_request` hooks from Flask. These are general purpose hooks that allow the user to execute a function before the request is processed by the route handler, potentially bypassing the route handler completely, and after the route handler returns - modifying or even replacing the response. The primary use case for these hooks is to perform side effects, such as opening DB connections, start celery tasks etc., or to perform operations such as caching of responses.

## Before Request

The before request handler is a sync or async function that receives the `starlite.request.Request` instance before it
reaches the route handler function. It does not have to return a value, but if it does return a value other than `None`,
then the route handler will not be called and this value will instead be used for the response.

```python
from starlite import Starlite, Request


async def my_before_request_handler(request: Request) -> None:
    ...


app = Starlite(route_handlers=[...], before_request=my_before_request_handler)
```

## After Request

The after request handler is a sync or async function that receives the Response object - this can be either an instance
of `starlite.response.Response` or any subclass of the Starlette `Response` object, and returning a `Response` object.

```python
from starlite import Starlite, Response


async def my_after_request_handler(response: Response) -> Response:
    ...


app = Starlite(route_handlers=[...], after_request=my_after_request_handler)
```

## Overriding Handlers

You can configure a `before_request` and `after_request` handlers on each layer of your application - the starlite
application, on routers, controllers or individual route handlers.

Each layer overrides the layer above it - thus, the handlers defined for a specific function will override those defined
on its router, which will in turn override those defined on the app level.

```python
from starlite import Starlite, Router, Controller, get


# this overrides the router and app
class MyController(Controller):
    path = "/my-path"

    # this overrides the controller, router and app
    @get(after_request=..., before_request=...)
    def my_handler(self) -> None:
        ...


# this overrides the app, for all routes below the router these functions will be used
router = Router(route_handlers=[MyController], after_request=..., before_request=...)

# this is top level
app = Starlite(route_handlers=[router], after_request=..., before_request=...)
```
