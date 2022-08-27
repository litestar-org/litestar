# Path Parameters

Path parameters are parameters declared as part of the `path` component of the URL. They are declared using a simple
syntax `{param_name:param_type}`:

```python
from starlite import get
from pydantic import BaseModel


class User(BaseModel):
    ...


@get("/user/{user_id:int}")
def get_user(user_id: int) -> User:
    ...
```

In the above there are two components:

1. The path parameter is defined in the `@get` decorator, which declares both the parameter's name (`user_id`) and type (`int`).
2. The decorated function `get_user` defines a parameter with the same name as the parameter defined in the `path`
   kwarg.

The correlation of parameter name ensures that the value of the path parameter will be injected into the function when
it's called.

## Supported Path Parameter Types

Currently, the following types are supported: `int`, `float`, `str`, `uuid`.

The types declared in the path parameter and the function do not need to match 1:1 - as long as parameter inside the
function declaration is typed with a "higher" type to which the lower type can be coerced, this is fine. For example,
consider this:

```python
from datetime import datetime
from starlite import get
from pydantic import BaseModel


class Order(BaseModel):
    ...


@get(path="/orders/{from_date:int}")
def get_orders(from_date: datetime) -> list[Order]:
    ...
```

The parameter defined inside the `path` kwarg is typed as `int`, because the value passed as part of the request will be
a timestamp in milliseconds without any decimals. The parameter in the function declaration though is typed
as `datetime.datetime`. This works because the int value will be passed to a pydantic model representing the function
signature, which will coerce the int into a datetime. Thus, when the function is called it will be called with a
datetime typed parameter.

!!! note
    You only need to define the parameter in the function declaration if it's actually used inside the function. If the
    path parameter is part of the path, but the function doesn't use it, it's fine to omit it. It will still be validated
    and added to the openapi schema correctly.

## Extra Validation and Documentation for Path Params

If you want to add validation or enhance the OpenAPI documentation generated for a given path parameter, you can do
so using the [Parameter function](./3-the-parameter-function.md):

```python
from pydantic_openapi_schema.v3_1_0.example import Example
from pydantic_openapi_schema.v3_1_0.external_documentation import (
    ExternalDocumentation,
)
from starlite import get, Parameter
from pydantic import BaseModel, conint, Json


class Version(BaseModel):
    id: conint(ge=1, le=10)
    specs: Json


@get(path="/versions/{version:int}")
def get_product_version(
    version: int = Parameter(
        ge=1,
        le=10,
        title="Available Product Versions",
        description="Get a specific version spec from the available specs",
        examples=[Example(value=1)],
        external_docs=ExternalDocumentation(
            url="https://mywebsite.com/documentation/product#versions"
        ),
    )
) -> Version:
    ...
```

In the above example, `Parameter` is used to restrict the value of `version` to a range between 1 and 10, and then set
the `title`,`description`, `examples` and `externalDocs` sections of the OpenAPI schema.
