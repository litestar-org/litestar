# The Body Function

You can use the `Body` function to customize the OpenAPI documentation for the request body schema or to control its validation:

```python
from starlite import Body, post
from pydantic import BaseModel


class User(BaseModel):
    ...


@post(path="/user")
async def create_user(
    data: User = Body(title="Create User", description="Create a new user.")
) -> User:
    ...
```

The `Body` function is very similar to the [Parameter function](../3-parameters/3-the-parameter-function.md#the-parameter-function).
and it receives the following kwargs:

- `media_type`: An instance of the `starlite.enums.RequestEncodingType` enum. Defaults to `RequestEncodingType.JSON`.
- `examples`: A list of `Example` models.
- `external_docs`: A url pointing at external documentation for the given parameter.
- `content_encoding`: The content encoding of the value. Applicable on to string values.
  See [OpenAPI 3.1 for details](https://spec.openapis.org/oas/latest.html#schema-object).
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
