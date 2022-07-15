# Life Cycle Hooks

Life cycle hooks allows a user to execute a function at a certain point, as indicated by the hook's name, during the
request-response cycle.

## Before Request

The `before_request` hook runs immediately before calling the route handler function. It accepts either a sync or async
function that receives the `starlite.connection.Request` instance as its sole parameter. While the handler function
does not need to return a value, if it does return a value other than `None`, then the route handler will not be called
and this value will instead be used for the response. Thus, the `before_request` handler allows bypassing the route
handler selectively.

```python
from starlite import Starlite, Request


async def my_before_request_handler(request: Request) -> None:
    ...


app = Starlite(route_handlers=[...], before_request=my_before_request_handler)
```

## After Request

The `after_request` hook is called after the route handler function returned and the response object has been resolved.
It receives either a sync or async function that receives the `Response` object, which can be either an instance
of `starlite.response.Response` or any subclass of the Starlette `Response` object. This function must return
a `Response` object - either the one that was passed in, or a different one. The `after_response` hook allows users to
modify responses, e.g. placing cookies or headers on them, or even to completely replace them given certain conditions.

```python
from starlite import Starlite, Response


async def my_after_request_handler(response: Response) -> Response:
    ...


app = Starlite(route_handlers=[...], after_request=my_after_request_handler)
```

## After Response

The `after_response` hook is called after the response has been awaited, that is - after a response has been sent to the
requester. It receives either a sync or async function that receives the `Request` object. The function should not
return any values. This hook is meant for data post-processing, transmission of data to third party services, gathering
of metrics
etc.

```python
from starlite import Starlite, Request


async def my_after_response_handler(request: Request) -> None:
    ...


app = Starlite(route_handlers=[...], after_response=my_after_response_handler)
```

## Overriding Handlers

You can configure life cycle hook handlers on all layers of your application, that is - on the Starlite instance itself,
on routers, controllers or individual route handlers.

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
