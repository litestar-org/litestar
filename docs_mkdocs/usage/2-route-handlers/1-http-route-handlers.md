# HTTP Route Handlers

The most commonly used route handlers are those that handle http requests and responses. These route handlers all
inherit from the class [`starlite.handlers.http.HTTPRouteHandler`][starlite.handlers.http.HTTPRouteHandler], which
is aliased as the decorator called [`route`][starlite.handlers.route]:

```python
from starlite import HttpMethod, route


@route(path="/some-path", http_method=[HttpMethod.GET, HttpMethod.POST])
def my_endpoint() -> None:
    ...
```

As mentioned above, `route` does is merely an alias for `HTTPRouteHandler`, thus the below code is equivalent to the one
above:

```python
from starlite import HttpMethod, HTTPRouteHandler


@HTTPRouteHandler(path="/some-path", http_method=[HttpMethod.GET, HttpMethod.POST])
def my_endpoint() -> None:
    ...
```

## HTTP Route Handlers Kwargs

The `route` decorator **requires** an `http_method` kwarg, which is a member of the [`HttpMethod`][starlite.enums.HttpMethod] enum or a list of members, e.g. `HttpMethod.GET` or `[HttpMethod.PATCH, HttpMethod.PUT]`.

See the [API Reference][starlite.handlers.HTTPRouteHandler] for full details on the `route` decorator and the kwargs it accepts.

### Semantic Handler Decorators

Starlite also includes "semantic" decorators, that is, decorators the pre-set the `http_method` kwarg to a specific HTTP
verb, which correlates with their name:

- [`delete`][starlite.handlers.delete]
- [`get`][starlite.handlers.get]
- [`head`][starlite.handlers.head]
- [`patch`][starlite.handlers.patch]
- [`post`][starlite.handlers.post]
- [`put`][starlite.handlers.put]

These are used exactly like `route` with the sole exception that you cannot configure the `http_method` kwarg:

```python
from starlite import Partial, delete, get, patch, post, put, head
from pydantic import BaseModel


class Resource(BaseModel):
    ...


@get(path="/resources")
def list_resources() -> list[Resource]:
    ...


@post(path="/resources")
def create_resource(data: Resource) -> Resource:
    ...


@get(path="/resources/{pk:int}")
def retrieve_resource(pk: int) -> Resource:
    ...


@head(path="/resources/{pk:int}")
def retrieve_resource_head(pk: int) -> None:
    ...


@put(path="/resources/{pk:int}")
def update_resource(data: Resource, pk: int) -> Resource:
    ...


@patch(path="/resources/{pk:int}")
def partially_update_resource(data: Partial[Resource], pk: int) -> Resource:
    ...


@delete(path="/resources/{pk:int}")
def delete_resource(pk: int) -> None:
    ...
```

Although these decorators are merely subclasses of `starlite.handlers.http.HTTPRouteHandler` that pre-set
the `http_method`, using _get_, _patch_, _put_, _delete_ or _post_ instead of _route_ makes the code clearer and
simpler.

Furthermore, in the OpenAPI specification each unique combination of http verb (e.g. "GET", "POST" etc.) and path is
regarded as a distinct [operation](https://spec.openapis.org/oas/latest.html#operation-object), and each operation
should be distinguished by a unique `operationId` and optimally also have a `summary` and `description` sections.

As such, using the `route` decorator is discouraged. Instead, the preferred pattern is to share code using secondary
class methods or by abstracting code to reusable functions.

### Using Sync Handler Functions

You can use both sync and async functions as the base for route handler functions, but which should you use? and when?

If your route handler needs to perform an I/O operation (read or write data from or to a service / db etc.), the most
performant solution within the scope of an ASGI application, including Starlite, is going to be by using an async
solution for this purpose.

The reason for this is that async code, if written correctly, is **non-blocking**. That is, async code can be paused and
resumed, and it therefore does not interrupt the main event loop from executing (if written correctly). On the other
hand, sync I/O handling is often **blocking**, and if you use such code in your function it can create performance
issues.

In this case you should use the `sync_to_thread` option. What this does, is tell Starlite to run the sync function in a
separate async thread, where it can block but will not interrupt the main event loop's execution.

The problem with this though is that this will slow down the execution of your sync code quite dramatically - by between
%40-60%. So this is really quite far from performant. Thus, you should use this option **only** when your sync code
performs blocking I/O operations. If your sync code simply performs simple tasks, non-expensive calculations, etc. you
should not use the `sync_to_thread` option.
