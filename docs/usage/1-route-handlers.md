# Route Handlers

Route handlers are the core of Starlite. They are constructed by decorating a function or method with one of the handler
decorators exported from Starlite.

## The Route Decorator

The base decorator is called `route`:

```python
from starlite import HttpMethod, route


@route(path="/my-endpoint", http_method=[HttpMethod.GET, HttpMethod.POST])
def my_endpoint():
    ...

```

What route does is wrap the given function or class method and replace it with an instance of the class `RouteHandler`.
In fact, route is merely an alias for `RouteHandler`, thus you could have done this instead:

```python
from starlite import HttpMethod, RouteHandler


@RouteHandler(path="/my-endpoint", http_method=[HttpMethod.GET, HttpMethod.POST])
def my_endpoint():
    ...

```

The `route` decorator receives the following kwargs -

* `path` (**required**) - a path string, with or without [path parameters](#path-parameters).
* `http_method` (**required**) - a member of the `HttpMethod` enum or a list of members, e.g. `HttpMethod.GET`
  or `[HttpMethod.Patch, HttpMethod.Put]`.
* `status_code`: the status code for a success response. If not specified, a default value will be used:
  HTTP_200_OK for _get_, _put_ and _patch_, HTTP_204_NO_CONTENT for _delete_, and HTTP_201_CREATED for _post_. **
  Important note**: if you specify more than one http method, as in the example above, you must specify the status_code
  to use for the response.
* `media_type`: A string or a member of the enum `starlite.MediaType`, which specifies the MIME Media Type for the
  response. Defaults to `MediaType.JSON`.
* `response_class`: The response class to use. The value must be either a `Starlette` response class or a class that
  extends it. Defaults to `starlite.Response`.
* `response_headers`: A _dataclass_ or _pydantic model_ that describes the response headers. This value is used only in
  the OpenAPI schema. Defaults to `None`.
* `dependencies`: A dictionary mapping dependency injection Providers to keys. Defaults to `None`.
* `include_in_schema`: A boolean flag dictating whether the given route handler will appear in the generated OpenAPI
  schema. Defaults to `True`.
* `tags`: a list of openapi-pydantic `Tag` models, which correlate to
  the [tag specification](https://spec.openapis.org/oas/latest.html#tag-object). Defaults to `None`.
* `summary`: Text used for the route's schema _summary_ section. Defaults to `None`.
* `description`: Text used for the route's schema _description_ section. Defaults to `None`.
* `operation_id`: An identifier used for the route's schema _operationId_. Defaults to `None`. Because this is a
  required OpenAPI value, if it's not provided by the user, the function/method's name will be used.
* `deprecated`: A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema. Defaults
  to `False`.
* `raises`: A list of exception classes extending from `starlite.HttpException`. This list should describe all
  exceptions raised within the route handler's function/method. The Starlite `ValidationException` will be added
  automatically for the schema if any validation is involved.

## Semantic Handler Decorators

Starlite also includes the following decorators, which as their names suggest already pre-set the `http_method` kwarg:

* `delete`
* `get`
* `patch`
* `post`
* `put`

```python
from starlite import delete, get, patch, post, put


@get(path="/resources")
def list_resources():
    ...

@post(path="/resources")
def create_resource():
    ...

@get(path="/resources/{pk:int}")
def retrieve_resource(pk: int):
    ...

@put(path="/resources/{pk:int}")
def update_resource(pk: int):
    ...

@patch(path="/resources/{pk:int}")
def partially_update_resource(pk: int):
    ...

@delete(path="/resources/{pk:int}")
def delete_resource(pk: int):
    ...
```

Although these decorators are merely subclasses of `PathHandler` that pre-set the `http_method`, using  _get_, _patch_
, _put_, _delete_ or _post_ instead of _route_ makes the code clearer and simpler.

Furthermore, in the OpenAPI specification each unique combination of http verb (e.g. "GET", "POST" etc.) and path is
regarded as a distinct [operation](https://spec.openapis.org/oas/latest.html#operation-object), and each operation
should be distinguished by a unique `operationId` and optimally also have a `summary` and `description` sections.

As such, using the `route` decorator is discouraged. Instead, the preferred pattern is to share code using secondary
class methods or by abstracting code to reusable functions.

## Parameters

While the handler decorators discussed above wrap a function or method, it's the job of that function or method to
handle the request. To this end it needs access to various data that is part of the request. This data will be injected
into the function by Starlite based on the names of the kwargs and their typings.

### Path Parameters

Defining path parameters is straightforward:

```python
from starlite import get


@get(path="/user/{user_id:int}")
def get_user(user_id: int):
    ...
```

In the above there are two components:

First, the path parameter is defined inside the `path` kwarg passed to the _@get_ decorator inside curly brackets and
following the form `{parameter_name:parameter_type}`. This definition of the path parameter is based on
the [Starlette path parameter](https://www.starlette.io/routing/#path-parameters)
mechanism. Yet, in difference to Starlette, which allows defining path parameters without defining their types, Starlite
enforces this typing, with the following types supported: _int_, _float_, _str_, _uuid_.

Second, the `get_user` function defines a parameter with the same name as defined in the `path` kwarg. This ensures that
the value of the path parameter will be injected into the function when it's called.

The types do not need to match 1:1 - as long as you type your parameter inside the function declaration with a high type
this should be ok. For example, consider this:

```python
from datetime import datetime

from starlite import get


@get(path="/orders/{from_date:int}")
def get_orders(from_date: datetime):
    ...
```

The parameter defined inside the `path` kwarg is typed as int, because the value passed from the frontend will be a
timestamp in milliseconds. The parameter in the function declaration though is typed as `datetime.datetime`. This is
fine- the int value will be passed to a pydantic model representing the function signature, which will coerce the int
into a datetime. Thus, when the function is called it will be called with a datetime typed parameter.

You should note that you only need to define the parameter in the function declaration if it's actually used inside the
function. If the path parameter is part of the path, but you do not actually need to use it in your business logic, it's
fine to omit it from the function declaration - it will still be validated and added to the openapi schema correctly.

If you do want to add validation or enhance the OpenAPI documentation generated for a given path parameter, you can do
so using the `Parameter` function exported from Starlite:

```python
from starlite import get, Parameter


@get(path="/versions/{version:int}")
def get_product_version(version: int = Parameter(
    ge=1,
    le=10,
    title="Available Product Versions",
    description="Get a specific specification version spec from the available specs",
    example=1,
    examples=[1, 2, 3],
    external_docs="https://mywebsite.com/documentation/product#versions",
)
):
    ...
```

In the above example, `Parameter` is used to restrict version to range between 1 and 10, and then set the title,
description, example, examples and externalDocs sections of the schema. For more details about this function,
see [Parameter](#the-parameter-function).

### Query Parameters

To define query parameters simply define them as `kwargs` in your function declaration:

```python
from datetime import datetime
from typing import List, Optional

from starlite import get


@get(path="/orders")
def get_orders(
        page: int,
        brands: List[str],
        page_size: int = 10,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
):
    ...
```

The above example is a rather classic example of a paginated get request:

1. _page_ is a required query parameter of type int. It has no default value and as such has to be given.
2. _page_size_ is a required query parameter of type int as well, but it has a default value - so it can be omitted in
   the request.
3. _brands_ is an optional list of strings with a default None value.
4. _from_date_ and _to_date_ or optional date-time values that have a default None value.

These parameters will be parsed from the function signature and used to generate a pydantic model. This model in turn
will be used to validate the parameters, and also to generate the OpenAPI schema for this endpoint.

This means that you can also use any pydantic type in the signature, and it will follow the same kind of validation and
parsing as you would get from pydantic.

This works great, but what happens when the request is sent with a non-python naming scheme, such as camelCase? You
could of course simply name your variables accordingly:

```python
from datetime import datetime
from typing import Optional, List

from starlite import get


@get(path="/orders")
def get_orders(
        page: int,
        brands: List[str],
        pageSize: int = 10,
        fromDate: Optional[datetime] = None,
        toDate: Optional[datetime] = None
):
    ...
```

This doesn't look so well, and tools such as PyLint will complain. The solution here is to use `Parameter`:

```python
from datetime import datetime
from typing import Optional, List

from starlite import get, Parameter


@get(path="/orders")
def get_orders(
        page: int,
        page_size: int = Parameter(query="pageSize", gt=0, le=100),
        brands: List[str] = Parameter(min_items=2, max_items=5),
        from_Date: Optional[datetime] = Parameter(query="fromDate"),
        to_date: Optional[datetime] = Parameter(query="fromDate")
):
    ...
```

As you can see, specifying the "query" kwarg to parameter allows us to remap from one key to another. Furthermore, you
can use Parameter for extended validation and documentation.

### Header and Cookie Parameters

Unlike Query parameters, Header and Cookie parameters have to be declared using the `Parameter` function, for example:

```python
from pydantic import UUID4
from starlite import get, Parameter


@get(path="/users/{user_id:uuid}/")
async def get_user(
        user_id: UUID4,
        token: Parameter(header="X-API-KEY"),
):
    ...
```

OR

```python
from pydantic import UUID4
from starlite import get, Parameter


@get(path="/users/{user_id:uuid}/")
async def get_user(
        user_id: UUID4,
        cookie: Parameter(cookie="my-cookie-param"),
):
    ...
```

The reason for this is that it's not possible to infer query parameters correctly without limiting header and cookie to
follow this pattern.

### The Parameter Function

The Parameter (named like a class for aesthetic reasons) is a wrapper on top of the
pydantic [Field](https://pydantic-docs.helpmanual.io/usage/schema/#field-customization) function. As such, you can use
most of the kwargs of Field (`alias` and `extra` are removed) with Parameter and have an identical result - the
additional kwargs accepted by `Parameter` are passed to the resulting pydantic `FieldInfo` as an `extra` dictionary and
have no effect on the working of pydantic itself.

`Parameter` accepts the following optional kwargs:

* `header`: The header parameter key for this parameter. A value for this kwarg is required for header parameters.
* `cookie`: The cookie parameter key for this parameter. A value for this kwarg is required for cookie parameters.
* `query`: The query parameter key for this parameter.
* `example`: An example value.
* `examples`: A list of example values.
* `external_docs`: A url pointing at external documentation for the given parameter.
* `content_encoding`: The content encoding of the value. Applicable on to string values.
  See [OpenAPI 3.1 for details](https://spec.openapis.org/oas/latest.html#schema-object).
* `required`: A boolean flag dictating whether this parameter is required. If set to `False`, None values will be
  allowed. Defaults to `True`.
* `default`: Default value.
* `default_factory`: A parameter less function that returns a default value.
* `title`: String value used in the `title` section of the OpenAPI schema for the given parameter.
* `description`: String value used in the `description` section of the OpenAPI schema for the given parameter.
* `const`: A boolean flag dictating whether this parameter is a constant. If `True`, the value passed to the parameter
  must equal its `default` value. This also populates the OpenAPI `const` field.
* `gt`: Constrict value to be _greater than_ a given float or int. Equivalent to `exclusiveMinimum` in the OpenAPI
  specification.
* `ge`: Constrict value to be _greater or equal to_ a given float or int. Equivalent to `minimum` in the OpenAPI
  specification.
* `lt`: Constrict value to be _less than_ a given float or int. Equivalent to `exclusiveMaximum` in the OpenAPI
  specification.
* `le`: Constrict value to be _less or equal to_ a given float or int. Equivalent to `maximum` in the OpenAPI
  specification.
* `multiple_of`: Constrict value to a multiple of a given gloat or int. Equivalent to `multipleOf` in the OpenAPI
  specification.
* `min_items`: Constrict a set or a list to have a minimum number of items. Equivalent to `minItems` in the OpenAPI
  specification.
* `max_items`: Constrict a set or a list to have a maximum number of items. Equivalent to `maxItems` in the OpenAPI
  specification.
* `min_length`: Constrict a string or bytes value to have a minimum length. Equivalent to `minLength` in the OpenAPI
  specification.
* `max_length`: Constrict a string or bytes value to have a maximum length. Equivalent to `maxLength` in the OpenAPI
  specification.
* `regex`: A string representing a regex against which the given string will be matched. Equivalent to `pattern` in the
  OpenAPI specification.
