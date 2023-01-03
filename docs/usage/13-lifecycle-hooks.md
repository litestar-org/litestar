# Life Cycle Hooks

Life cycle hooks allows a user to execute a function at a certain point, as indicated by the hook's name, during the
request-response cycle.

## Before Request

The `before_request` hook runs immediately before calling the route handler function. It accepts either a sync or async
function that receives the [`Request`][starlite.connection.Request] instance as its sole parameter.
While the handler function does not need to return a value, if it does return a value other than `None`, then the route
handler will not be called and this value will instead be used for the response, which allows the `before_request` handler
to bypass a route handler.

```py
--8<-- "examples/lifecycle_hooks/before_request.py"
```

## After Request

The `after_request` hook is called after the route handler function returned and the response object has been resolved.
It receives either a sync or async function that receives the `Response` object, which can be either an instance
of `starlite.response.Response` or any subclass of the Starlette `Response` object. This function must return
a `Response` object - either the one that was passed in, or a different one. The `after_response` hook allows users to
modify responses, e.g. placing cookies or headers on them, or even to completely replace them given certain conditions.

```py
--8<-- "examples/lifecycle_hooks/after_request.py"
```

## After Response

The `after_response` hook is called after the response has been awaited, that is - after a response has been sent to the
requester. It receives either a sync or async function that receives the [`Request`][starlite.connection.Request]
object. The function should not return any values. This hook is meant for data post-processing, transmission of data to third party
services, gathering of metrics etc.

```python
from starlite import Starlite, Request


async def my_after_response_handler(request: Request) -> None:
    ...


app = Starlite(route_handlers=[...], after_response=my_after_response_handler)
```


## Layered hooks


!!! info "Layered architecture"
    Life cycle hooks are part of Starlite's layered architecture, which means you can
    set them on every layer of the application. If you set hooks on multiple layers, 
    the layer closest to the route handler will take precedence.

    You can read more about this here:
    [Layered architecture](/starlite/usage/0-the-starlite-app#layered-architecture)


```py
--8<-- "examples/lifecycle_hooks/layered_hooks.py"
```

