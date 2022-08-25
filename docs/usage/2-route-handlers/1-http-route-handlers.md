# HTTP Route Handlers

The most commonly used route handlers are those that handle http requests and responses. These route handlers all
inherit from the class `starlite.handlers.http.HTTPRouteHandler`, which is aliased as the decorator called `route`:

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

The `route` decorator **requires** an `http_method` kwarg, which is a member of the enum `starlite.enums.HttpMethod` or
a list of members, e.g. `HttpMethod.GET` or `[HttpMethod.PATCH, HttpMethod.PUT]`.

Additionally, you can pass the following optional kwargs:

- `status_code`: the status code for a success response. If not
  specified, [a default value will be used](../5-responses/0-responses-intro.md#status-codes).
- `media_type`: A string or a member of the enum `starlite.enums.MediaType`, which specifies the MIME Media Type for the
  response. Defaults to `MediaType.JSON`. See [media-type](../5-responses/0-responses-intro.md#media-type).
- `response_class`: A custom response class to be used as the app default.
  See [using-custom-responses](../5-responses/0-responses-intro.md#using-custom-responses).
- `response_headers`: A dictionary of `ResponseHeader` instances.
  See [response-headers](../5-responses/0-responses-intro.md#response-headers).
- `response_cookies`: A list of `Cookie` instances. See [response-cookies](../5-responses/5-response-cookies.md)
- `dependencies`: A dictionary mapping dependency providers.
  See [dependency-injection](../6-dependency-injection/0-dependency-injection-intro.md).
- `opt`: String keyed dictionary of arbitrary value that can be used by [guards](../9-guards.md).
- `guards`: A list of [guards](../9-guards.md).
- `middleware`: A list of [middlewares](../7-middleware/0-middleware-intro.md).
- `name`: A unique name that identifies the route handler. See: [route handler indexing](4-route-handler-indexing.md).
- `before_request`: a sync or async callable executed before a `Request` is passed to a route handler (method) on the
  controller. If the callable returns a value, the request will not reach the route handler, and instead this value
  will be used.
- `after_request`: a sync or async callable to execute before the `Response` is returned. The callable receives the
  `Response` object and it must return a `Response` object.
- `after_response`: a sync or async callable executed after the `Response` is returned. The callable receives the
  original `Request` object, and should return `None`.
  `Respose` object and it must return a `Response` object.
- `background`: A callable wrapped in an instance of `starlite.datastructures.BackgroundTask` or a list
  of `BackgroundTask` instances wrapped in `starlite.datastructures.BackgroundTasks`. The callable(s) will be called after
  the response is executed. Note - if you return a value from a `before_request` hook, background tasks passed to the
  handler will not be executed.
- `sync_to_thread`: A boolean dictating whether the handler function will be executed in a worker thread or the main
  event loop. This has an effect only for sync handler functions.
  See [using sync handler functions](#using-sync-handler-functions).
- `exception_handlers`: A dictionary mapping exceptions or exception codes to handler functions.
  See [exception-handlers](../17-exceptions#exception-handling).
- `cache`: Enables response caching if configured on the application level. Valid values are 'true' or a number
  of seconds (e.g. '120') to cache the response. See [caching](../16-caching.md)
- `cache_key_builder`: A cache key building function. Allows for customization of the cache key if caching is
  configured on the application level. See [caching](../16-caching.md)

And the following kwargs, which affect [OpenAPI schema generation](../12-openapi.md#route-handler-configuration)

- `include_in_schema`: A boolean flag dictating whether the given route handler will appear in the generated OpenAPI
  schema. Defaults to `True`.
- `tags`: a list of openapi-pydantic `Tag` models, which correlate to the
- [tag specification](https://spec.openapis.org/oas/latest.html#tag-object).
- `summary`: Text used for the route's schema _summary_ section.
- `description`: Text used for the route's schema _description_ section.
- `response_description`: Text used for the route's response schema _description_ section.
- `operation_id`: An identifier used for the route's schema _operationId_. Defaults to the `__name__` of the wrapped
  function.
- `deprecated`: A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema. Defaults
  to `False`.
- `raises`: A list of exception classes extending from `starlite.HttpException`. This list should describe all
  exceptions raised within the route handler's function/method. The Starlite `ValidationException` will be added
  automatically for the schema if any validation is involved.
- `content_encoding`: A string describing the encoding of the content, e.g. "base64".
- `content_media_type`: A string designating the media-type of the content, e.g. "image/png".

### Semantic Handler Decorators

Starlite also includes "semantic" decorators, that is, decorators the pre-set the `http_method` kwarg to a specific HTTP
verb, which correlates with their name:

- `delete`
- `get`
- `patch`
- `post`
- `put`

These are used exactly like `route` with the sole exception that you cannot configure the `http_method` kwarg:

```python
from starlite import Partial, delete, get, patch, post, put
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

If your route handler needs to perform an I/O operation (read or write data from or to a service / db etc.), he most
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
