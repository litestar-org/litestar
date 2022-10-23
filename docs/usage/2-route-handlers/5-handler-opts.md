# Handler 'opts'

All route handler decorators accept a key called `opt` which accepts a dictionary of arbitrary values, e.g.

```python
from starlite import get


@get("/", opt={"my_key": "some-value"})
def handler() -> None:
    ...
```

This dictionary can be accessed by [route guard](../9-guards.md), or by accessing the `route_handler` property on a
[request][starlite.connection.request.Request] (`request.route_handler.opt`), or using the
[ASGI scope][starlite.types.Scope] object directly (`scope["route_handler"].opt`).

## Passing **kwargs to handlers

Building on `opts`, you can pass any arbitrary kwarg to the route handler decorator, and it will be automatically set
as a key in the opt dictionary:

```python
from starlite import get


@get("/", my_key="some-value")
def handler() -> None:
    ...


assert handler.opt["my_key"] == "some-value"
```
