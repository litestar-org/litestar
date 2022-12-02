# Route Handlers

Route handlers are the core of Starlite. They are constructed by decorating a function or class method with one of the
handler decorators exported from Starlite.

For example:

```python
from starlite import MediaType, get


@get("/", media_type=MediaType.TEXT)
def greet() -> str:
    return "hello world"
```

In the above example, the decorator includes all the information required to define the endpoint operation for the
combination of the path `"/"` and the http verb `GET`. In this case it will be a http response with a "Content-Type"
header of `text/plain`.

What the decorator does, is wrap the function or method within a class instance that inherits from
[`BaseRouteHandler`][starlite.handlers.base.BaseRouteHandler]. These classes are optimized
descriptor classes that record all the data necessary for the given function or method - this includes a modelling of
the function signature, which allows for injection of kwargs and dependencies, as well as data pertinent to OpenAPI
spec generation.

## Declaring Path(s)

All route handler decorator accept an optional path argument. This argument can be declared as a kwarg using the `path`
key word:

```python
from starlite import get


@get(path="/some-path")
def my_route_handler() -> None:
    ...
```

It can also be passed as an argument without the key-word:

```python
from starlite import get


@get("/some-path")
def my_route_handler() -> None:
    ...
```

And the value for this argument can be either a string path, as in the above examples, or a list of string paths:

```python
from starlite import get


@get(["/some-path", "/some-other-path"])
def my_route_handler() -> None:
    ...
```

This is particularly useful when you want to have optional [path parameters](../3-parameters/0-path-parameters.md):

```python
from starlite import get


@get(
    ["/some-path", "/some-path/{some_id:int}"],
)
def my_route_handler(some_id: int = 1) -> None:
    ...
```

## Handler Function Kwargs

Route handler functions or methods access various data by declaring these as annotated function kwargs. The annotated
kwargs are inspected by Starlite and then injected into the request handler.

The following sources can be accessed using annotated function kwargs:

1. [path, query, header and cookie parameters](../3-parameters/3-the-parameter-function.md)
2. [request data](../4-request-data.md)
3. [dependencies](../6-dependency-injection/0-dependency-injection-intro.md)

Additionally, you can specify the following special kwargs, what's called "reserved keywords" internally:

- `cookies`: injects the request `cookies` as a parsed dictionary.
- `headers`: injects the request `headers` as an instance of [`Headers`][starlite.datastructures.headers.Headers],
  which is a case-insensitive mapping.
- `query`: injects the request `query_params` as a parsed dictionary.
- `request`: injects the [`Request`][starlite.connection.Request] instance. Available only for [http route handlers](1-http-route-handlers.md)
- `scope`: injects the ASGI scope dictionary.
- `socket`: injects the [`WebSocket`][starlite.connection.WebSocket] instance. Available only for [websocket handlers](2-websocket-route-handlers.md)
- `state`: injects a copy of the application `state`.

For example:

```python
from typing import Any, Dict
from starlite import State, Request, get
from starlite.datastructures import Headers


@get(path="/")
def my_request_handler(
    state: State,
    request: Request,
    headers: Headers,
    query: Dict[str, Any],
    cookies: Dict[str, Any],
) -> None:
    ...
```

!!! tip
    You can define a custom typing for your application state and then use it as a type instead of just using the
    State class from Starlite

## Handler Function Type Annotations

Starlite enforces strict type annotations. Functions decorated by a route handler **must** have all their kwargs and
return value type annotated. If a type annotation is missing, an
[`ImproperlyConfiguredException`][starlite.exceptions.ImproperlyConfiguredException] will be raised during the
application boot-up process.

There are several reasons for why this limitation is enforced:

1. to ensure best practices
2. to ensure consistent OpenAPI schema generation
3. to allow Starlite to compute during the application bootstrap all the kwargs required by a function
