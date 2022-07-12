# Parameters

## Path Parameters

```python
from starlite import get

from my_app.models import User


@get(path="/user/{user_id:int}")
def get_user(user_id: int) -> User:
    ...
```

In the above there are two components:

1. The path parameter is defined inside the `path` kwarg passed to the _@get_ decorator in the
   form `{parameter_name:parameter_type}`. This definition of the path parameter is based on
   the [Starlette path parameter](https://www.starlette.io/routing/#path-parameters)
   mechanism. Yet, in difference to Starlette, which allows defining path parameters without defining their types,
   Starlite
   enforces this typing, with the following types supported: `int`, `float`, `str`, `uuid`.
2. The `get_user` function defines a parameter with the same name as defined in the `path` kwarg. This ensures that
   the value of the path parameter will be injected into the function when it's called.

The types do not need to match 1:1 - as long as parameter inside the function declaration is typed with a "higher" type
to which the lower type can be coerced, this is fine. For example, consider this:

```python
from datetime import datetime
from typing import List

from starlite import get

from my_app.models import Order


@get(path="/orders/{from_date:int}")
def get_orders(from_date: datetime) -> List[Order]:
    ...
```

The parameter defined inside the `path` kwarg is typed as `int`, because the value passed from the frontend will be a
timestamp in milliseconds without any decimals. The parameter in the function declaration though is typed
as `datetime.datetime`. This works because the int value will be passed to a pydantic model representing the function
signature, which will coerce the int
into a datetime. Thus, when the function is called it will be called with a datetime typed parameter.

<!-- prettier-ignore -->
!!! note
    You only need to define the parameter in the function declaration if it's actually used inside the
    function. If the path parameter is part of the path, but the function doesn't use it, its fine to omit it.
    It will still be validated and added to the openapi schema correctly.

### Extra Validation and Documentation for Path Params

If you want to add validation or enhance the OpenAPI documentation generated for a given path parameter, you can do
so using the [Parameter function](#the-parameter-function):

```python
from openapi_schema_pydantic.v3.v3_1_0.example import Example
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

In the above example, `Parameter` is used to restrict the value of `version` to a range between 1 and 10, and then set
the `title`,
`description`, `examples` and `externalDocs` sections of the OpenAPI schema.

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

The above is a rather classic example of a paginated "GET" request:

1. _page_ is a required query parameter of type `int`. It has no default value and as such has to be provided or a
   ValidationException will be raised.
2. _page_size_ is a required query parameter of type `int` as well, but it has a default value - so it can be omitted in
   the request.
3. _brands_ is an optional list of strings with a default `None` value.
4. _from_date_ and _to_date_ are optional date-time values that have a default `None` value.

These parameters will be parsed from the function signature and used to generate a pydantic model. This model in turn
will be used to validate the parameters and generate the OpenAPI schema.

This means that you can also use any pydantic type in the signature, and it will follow the same kind of validation and
parsing as you would get from pydantic.

This works great, but what happens when the request is sent with a non-python naming scheme, such as _camelCase_? You
could of course simply rename your variables accordingly:

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

This doesn't look so good, and tools such as PyLint will complain. The solution here is to
use [the Parameter function](#the-parameter-function):

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

As you can see, specifying the "query" kwarg allows us to remap from one key to another. Furthermore, we can use
Parameter for extended validation and documentation, as is done for `page_size`.

## Header and Cookie Parameters

Unlike _Query_ parameters, _Header_ and _Cookie_ parameters have to be declared
using [the Parameter function](#the-parameter-function), for example:

```python
from pydantic import UUID4
from starlite import get, Parameter

from my_app.models import User


@get(path="/users/{user_id:uuid}/")
async def get_user(
    user_id: UUID4,
    token: str = Parameter(header="X-API-KEY"),
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
    cookie: str = Parameter(cookie="my-cookie-param"),
) -> User:
    ...
```

As you can see in the above, header parameters are declared using the `header` kwargs and cookie parameters using
the `cookie` kwarg. Aside form this difference they work the same as query parameters.

## The Parameter Function

`Parameter` is a wrapper on top of the
pydantic [Field function](https://pydantic-docs.helpmanual.io/usage/schema/#field-customization) that extends it with a
set of Starlite specific kwargs. As such, you can use
most of the kwargs of _Field_ with Parameter and have the same parsing and validation. The additional kwargs accepted
by `Parameter` are passed to the resulting pydantic `FieldInfo` as an `extra`
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

## Layered Parameters

Starlite has a "layered" architecture, which is also evident in that one can declare parameters not only in individual
route handlers - as in the above example, but on different layers of the application:

```python
from starlite import Starlite, Controller, Router, Parameter


class MyController(Controller):
    path = "/controller"
    parameters = {
        "controller_param": Parameter(int, lt=100),
    }

    @get("/{path_param:int}")
    def my_handler(
        self,
        path_param: int,
        local_param: str,
        router_param: str,
        controller_param: int = Parameter(int, lt=50),
    ) -> dict:
        ...


router = Router(
    path="/router",
    route_handlers=[MyController],
    parameters={
        "router_param": Parameter(
            str, regex="^[a-zA-Z]$", header="MyHeader", required=False
        ),
    },
)

app = Starlite(
    route_handlers=[router],
    parameters={
        "app_param": Parameter(str, cookie="special-cookie"),
    },
)
```

In the above we declare parameters on the app, router and controller levels in addition to those declared in the route
handler. Lets look at these closer:

`app_param` is a cookie param with the key `special-cookie`. We type it as `str` by passing this as a arg to
the `Parameter` function. This is required for us to get typing in the OpenAPI docs. Additionally, this parameter is
assumed to be required because it is not explicitly declared as `required=False`. This is important because the route
handler function does not declare a parameter called `app_param` at all, but it will still require this param to be sent
as part of the request of validation will fail.

`router_param` is a header param with the key `MyHeader`. Because its declared as `required=False`, it will not fail
validation if not present unless explicitly declared by a route handler - and in this case it is. Thus it is actually
required for the router handler function that declares it as an `str` and not an `Optional[str]`. If a string value is
provided, it will be tested against the provided regex.

`controller_param` is a query param with the key `controller_param`. It has an `lt=100` defined on the controller, which
means the provided value must be less than 100. Yet the route handler redeclares it with an `lt=50`, which means for the
route handler this value must be less than 50.

Finally `local_param` is a route handler local query parameter, and `path_param` is a path parameter.

**Note**: You cannot declare path parameters in different application layers. The reason for this is to ensure
simplicity - otherwise parameter resolution becomes very difficult to do correctly.
