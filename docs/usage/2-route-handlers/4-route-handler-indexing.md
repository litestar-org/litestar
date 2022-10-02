# Route Handler Indexing

You can provide in all route handler decorators a `name` kwarg. The value for this kwarg **must be unique**, otherwise
an exception will be raised. Once a route handler defines `name`, this value can be used to dynamically retrieve (i.e.
during runtime) a mapping containing the route handler instance and the path, also it can be used to build a URL path
for that handler:

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

    # handler_index == { "path": "/", "handler" ... }
    # do something with the handler index below, e.g. send a redirect response to the handler, or access
    # handler.opt and some values stored there etc.

    return Redirect(path=handler_index["path"])


@get("/redirect/{param_value:int}", name="five")
def handler_five(request: Request, param_value: int) -> Redirect:
    path = request.app.route_reverse("three", param=param_value)
    return Redirect(path=path)


app = Starlite(route_handlers=[handler_one, handler_two, handler_three])
```
