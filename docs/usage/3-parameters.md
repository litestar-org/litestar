# Parameters

## Path Parameters

Defining path parameters is straightforward:

```python
from starlite import get

from my_app.models import User


@get(path="/user/{user_id:int}")
def get_user(user_id: int) -> User:
    ...
```

In the above there are two components:

First, the path parameter is defined inside the `path` kwarg passed to the _@get_ decorator. This is done following the
form `{parameter_name:parameter_type}`. This definition of the path parameter is based on
the [Starlette path parameter](https://www.starlette.io/routing/#path-parameters)
mechanism. Yet, in difference to Starlette, which allows defining path parameters without defining their types, Starlite
enforces this typing, with the following types supported: _int_, _float_, _str_, _uuid_.

Second, the `get_user` function defines a parameter with the same name as defined in the `path` kwarg. This ensures that
the value of the path parameter will be injected into the function when it's called.

The types do not need to match 1:1 - as long as you type your parameter inside the function declaration with a high type
this should be ok. For example, consider this:

```python
from datetime import datetime
from typing import List

from starlite import get

from my_app.models import Order


@get(path="/orders/{from_date:int}")
def get_orders(from_date: datetime) -> List[Order]:
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
from openapi_schema_pydantic import Example
from starlite import get, Parameter

from my_app.models import Version


@get(path="/versions/{version:int}")
def get_product_version(
    version: int = Parameter(
        ge=1,
        le=10,
        title="Available Product Versions",
        description="Get a specific specification version spec from the available specs",
        examples=[Example(value=1)],
        external_docs="https://mywebsite.com/documentation/product#versions",
    )
) -> Version:
    ...
```

In the above example, `Parameter` is used to restrict version to range between 1 and 10, and then set the title,
description, examples and externalDocs sections of the schema. For more details,
see [Parameter](#the-parameter-function).

## Query Parameters

To define query parameters simply define them as kwargs in your function declaration:

```python
from datetime import datetime
from typing import List, Optional

from starlite import get

from my_app.models import Order


@get(path="/orders")
def get_orders(
    page: int,
    brands: List[str],
    page_size: int = 10,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
) -> List[Order]:
    ...
```

The above example is a rather classic example of a paginated GET request:

1. _page_ is a required query parameter of type int. It has no default value and as such has to be given.
2. _page_size_ is a required query parameter of type int as well, but it has a default value - so it can be omitted in
   the request.
3. _brands_ is an optional list of strings with a default `None` value.
4. _from_date_ and _to_date_ are optional date-time values that have a default `None` value.

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

from my_app.models import Order


@get(path="/orders")
def get_orders(
    page: int,
    brands: List[str],
    pageSize: int = 10,
    fromDate: Optional[datetime] = None,
    toDate: Optional[datetime] = None,
) -> List[Order]:
    ...
```

This doesn't look so well, and tools such as PyLint will complain. The solution here is to use `Parameter`:

```python
from datetime import datetime
from typing import Optional, List

from starlite import get, Parameter

from my_app.models import Order


@get(path="/orders")
def get_orders(
    page: int,
    page_size: int = Parameter(query="pageSize", gt=0, le=100),
    brands: List[str] = Parameter(min_items=2, max_items=5),
    from_Date: Optional[datetime] = Parameter(query="fromDate"),
    to_date: Optional[datetime] = Parameter(query="fromDate"),
) -> List[Order]:
    ...
```

As you can see, specifying the "query" kwarg to parameter allows us to remap from one key to another. Furthermore, you
can use Parameter for extended validation and documentation.

## Header and Cookie Parameters

Unlike Query parameters, Header and Cookie parameters have to be declared using the `Parameter` function, for example:

```python
from pydantic import UUID4
from starlite import get, Parameter

from my_app.models import User


@get(path="/users/{user_id:uuid}/")
async def get_user(
    user_id: UUID4,
    token: Parameter(header="X-API-KEY"),
) -> User:
    ...
```

OR

```python
from pydantic import UUID4
from starlite import get, Parameter

from my_app.models import User


@get(path="/users/{user_id:uuid}/")
async def get_user(
    user_id: UUID4,
    cookie: Parameter(cookie="my-cookie-param"),
) -> User:
    ...
```

The reason for this is that it's not possible to infer query parameters correctly without limiting header and cookie to
follow this pattern.

## The Parameter Function

The Parameter is a wrapper on top of the
pydantic [Field](https://pydantic-docs.helpmanual.io/usage/schema/#field-customization) function. As such, you can use
most of the kwargs of Field (`alias`, `extra` and `default_factory` are removed) with Parameter and have an identical
result - the additional kwargs accepted by `Parameter` are passed to the resulting pydantic `FieldInfo` as an `extra`
dictionary and have no effect on the working of pydantic itself.

`Parameter` accepts the following optional kwargs:

- `header`: The header parameter key for this parameter. A value for this kwarg is required for header parameters.
- `cookie`: The cookie parameter key for this parameter. A value for this kwarg is required for cookie parameters.
- `query`: The query parameter key for this parameter.
- `examples`: A list of `Example` models.
- `external_docs`: A url pointing at external documentation for the given parameter.
- `content_encoding`: The content encoding of the value. Applicable on to string values.
  See [OpenAPI 3.1 for details](https://spec.openapis.org/oas/latest.html#schema-object).
- `required`: A boolean flag dictating whether this parameter is required. If set to `False`, None values will be
  allowed. Defaults to `True`.
- `default`: A default value. If `const` is true, this value is required.
- `title`: String value used in the `title` section of the OpenAPI schema for the given parameter.
- `description`: String value used in the `description` section of the OpenAPI schema for the given parameter.
- `const`: A boolean flag dictating whether this parameter is a constant. If `True`, the value passed to the parameter
  must equal its `default` value. This also causes the OpenAPI `const` field to be populated with the `default` value.
- `gt`: Constrict value to be _greater than_ a given float or int. Equivalent to `exclusiveMinimum` in the OpenAPI
  specification.
- `ge`: Constrict value to be _greater or equal to_ a given float or int. Equivalent to `minimum` in the OpenAPI
  specification.
- `lt`: Constrict value to be _less than_ a given float or int. Equivalent to `exclusiveMaximum` in the OpenAPI
  specification.
- `le`: Constrict value to be _less or equal to_ a given float or int. Equivalent to `maximum` in the OpenAPI
  specification.
- `multiple_of`: Constrict value to a multiple of a given float or int. Equivalent to `multipleOf` in the OpenAPI
  specification.
- `min_items`: Constrict a set or a list to have a minimum number of items. Equivalent to `minItems` in the OpenAPI
  specification.
- `max_items`: Constrict a set or a list to have a maximum number of items. Equivalent to `maxItems` in the OpenAPI
  specification.
- `min_length`: Constrict a string or bytes value to have a minimum length. Equivalent to `minLength` in the OpenAPI
  specification.
- `max_length`: Constrict a string or bytes value to have a maximum length. Equivalent to `maxLength` in the OpenAPI
  specification.
- `regex`: A string representing a regex against which the given string will be matched. Equivalent to `pattern` in the
  OpenAPI specification.
