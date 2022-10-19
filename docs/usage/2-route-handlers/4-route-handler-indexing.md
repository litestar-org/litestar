# Route Handler Indexing

You can provide in all route handler decorators a `name` kwarg. The value for this kwarg **must be unique**, otherwise
[`ImproperlyConfiguredException`][starlite.exceptions.ImproperlyConfiguredException] exception will be raised. Default
value for `name` is value returned by `handler.__str__` which should be the full dotted path to the handler
(e.g. `app.controllers.projects.list` for `list` function residing in `app/controllers/projects.py` file). `name` can
be used to dynamically retrieve (i.e. during runtime) a mapping containing the route handler instance and paths, also
it can be used to build a URL path for that handler:

```python
from starlite import Starlite, Request, Redirect, NotFoundException, get


@get("/abc", name="one")
def handler_one() -> None:
    pass


@get("/xyz", name="two")
def handler_two() -> None:
    pass


@get("/def/{param:int}", name="three")
def handler_three(param: int) -> None:
    pass


@get("/{handler_name:str}", name="four")
def handler_four(request: Request, name: str) -> Redirect:
    handler_index = request.app.get_handler_index_by_name(name)
    if not handler_index:
        raise NotFoundException(f"no handler matching the name {name} was found")

    # handler_index == { "paths": ["/"], "handler": ..., "qualname": ... }
    # do something with the handler index below, e.g. send a redirect response to the handler, or access
    # handler.opt and some values stored there etc.

    return Redirect(path=handler_index["paths"][0])


@get("/redirect/{param_value:int}", name="five")
def handler_five(request: Request, param_value: int) -> Redirect:
    path = request.app.route_reverse("three", param=param_value)
    return Redirect(path=path)


app = Starlite(route_handlers=[handler_one, handler_two, handler_three])
```

[`route_reverse`][starlite.app.Starlite.route_reverse] will raise
[`NoMatchRouteFoundException`][starlite.exceptions.NoRouteMatchFoundException] if route with given name was not found
or if any of path parameters is missing or if any of passed path parameters types do not match types in the respective
route declaration. However, `str` is accepted in place of `datetime`, `date`, `time`, `timedelta`, `float`, and `Path`
parameters, so you can apply custom formatting and pass the result to `route_reverse`.

If handler has multiple paths attached to it `route_reverse` will return the path that consumes the most number of
keywords arguments passed to the function.

```python
from starlite import get, Request


@get(
    ["/some-path", "/some-path/{id:int}", "/some-path/{id:int}/{val:str}"],
    name="handler_name",
)
def handler(id: int = 1, val: str = "default") -> None:
    ...


@get("/path-info")
def path_info(request: Request) -> str:
    path_optional = request.app.route_reverse("handler_name")
    # /some-path`

    path_partial = request.app.route_reverse("handler_name", id=100)
    # /some-path/100

    path_full = request.app.route_reverse("handler_name", id=100, val="value")
    # /some-path/100/value`

    return f"{path_optional} {path_partial} {path_full}"
```

If there are multiple paths attached to a handler that have the same path parameters (for example indexed handler
has been registered on multiple routers) the result of `route_reverse` is not defined.
The function will return a formatted path, but it might be picked randomly so reversing urls in such cases is highly
discouraged.

If you have access to `request` instance you can make reverse lookups using `url_for` function which is similar to
`route_reverse` but returns absolute URL.
