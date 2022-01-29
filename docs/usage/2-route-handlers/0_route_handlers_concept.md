# Route Handlers

Route handlers are the core of Starlite. They are constructed by decorating a function or class method with one of the handler
decorators exported from Starlite.

For example:

```python
from starlite import MediaType, get


@get("/", media_type=MediaType.TEXT)
def greet() -> str:
    return "hello world"
```

The decorator includes all the information required to define the endpoint operation for the combination of the path
`"/"` and the http verb `GET`. In this case it will be an http response with a "Content-Type" header of `text/plain`.

What the decorator does, is wrap the function or method within a class instance inheriting from
`starlite.handlers.BaseRouteHandler`. These classes are optimized descriptor classes that record all the data necessary
for the given function or method - this includes validation, and parameters passed to the decorator,
as well as information about the function signature.
