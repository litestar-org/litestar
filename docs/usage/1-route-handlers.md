# Route Handlers

Route handlers are the core of StarLite. These are functions or methods that have been decorated by one of the route
decorators exported by StarLite.

The base decorator is called `route`:

```python
from starlite import HttpMethod, route


@route(path="/my-endpoint", http_method=[HttpMethod.GET, HttpMethod.POST])
def my_endpoint():
    ...

```

What route does is wrap the given function or class method and replace it with an instance of the class `RouteHandler`.
In fact, route is merely an alias for `RouteHandler`, thus you could have done this instead (although less pythonic):

```python
from starlite import HttpMethod, RouteHandler


@RouteHandler(path="/my-endpoint", http_method=[HttpMethod.GET, HttpMethod.POST])
def my_endpoint():
    ...

```

The `route` decorator has two required kwargs -

* `path` - a path string, with or without [path parameters](2-parameter.md#path-parameters).
* `http_method` a member of the `HttpMethod` enum or a list of members, e.g. `HttpMethod.GET`
  or `[HttpMethod.Patch, HttpMethod.Put]`.

It also has the following optional kwargs:

* `status_code`: the status code for a success response. If not specified, a default value will be used:
  HTTP_200_OK for _get_, _put_ and _patch_, HTTP_204_NO_CONTENT for _delete_, and HTTP_201_CREATED for _post_. **
  Important note**: if you specify more than one http method, as in the example above, you must specify the status_code
  to use for the response.
* `media_type`: A string or a member of the enum `starlite.MediaType`, which specifies the MIME Media Type for the
  response. Defaults to `MediaType.JSON`.
* `response_class`: The response class to use. The value must be either a `Starlette` response class or a class that
  extends it. Defaults to `starlite.Response`.
* `response_headers`: A _dataclass_, _TypedDict_ or _pydantic model_ that describes the response headers. Defaults
  to `None`.
* `dependencies`: A dictionary mapping dependency injection Providers to keys. Defaults to `None`.
* `include_in_schema`: A boolean flag dictating whether the given route handler will appear in the generated OpenAPI
  schema. Defaults to `True`.
* `tags`: a list of openapi-pydantic `Tag` models, which correlate to
  the [tag specification](https://spec.openapis.org/oas/latest.html#tag-object). Defaults to `None`.
* `summary`: Text used for the route's schema _summary_ section. Defaults to `None`.
* `description`: Text used for the route's schema _description_ section. Defaults to `None`.
* `operation_id`: An identifier used for the route's schema _operationId_. Defaults to `None`. Because this is a
  required OpenAPI value, if it's not provided by the user, the function/method's name will be used.
* `deprecated`: A boolean dictating whether this route should be marked as deprecated in the schema. Defaults to `False`
  .
* `raises`: A list of exception classes extending from `starlite.HttpException`. This list should describe all
  exceptions raised within the route handler's function/method. The StarLite `ValidationException` will be added
  automatically for the schema if any validation is involved.

For convenience, StarLite also includes the following decorators:

* `delete`
* `get`
* `patch`
* `post`
* `put`

You use them exactly the same way, with the exception that these decorators do not accept `http_method` as a kwarg
because they already set it:

```python
from starlite import get, post


@get(path="/my-endpoint")
def my_get_handler():
    ...


@post(path="/my-endpoint")
def my_post_handler():
    ...
```

The distinct advantage of using _get_, _patch_, _put_, _delete_ or _create_ vis-à-vis _route_ is the clearer semantics.
Furthermore, in the OpenAPI specification each unique combination of http method (or verb) and path is regarded as a
distinct [operation](https://spec.openapis.org/oas/latest.html#operation-object). Each operation should be distinguished
by a unique `operationId` and optimally also have a `summary` and `description` sections. As such, using the route
decorator is discouraged. Instead, the preferred pattern is to share code using secondary class methods or by
abstracting code to reusable functions. Keeping the route handling functions as simple as possible.
Each unique combination of path+http method (or verb)
