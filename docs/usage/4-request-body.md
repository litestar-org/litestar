# Request Body

For all http requests, except GET requests, you can access the request body by specifying the `data` kwarg in your
handler function or method:

```python
from starlite import post

from my_app.models import User


@post(path="/user")
async def create_user(data: User) -> User:
    ...
```

Because `User` in the above example is a pydantic model you get the benefit of validation and a decent schema generation
out of the box.

## The Body Function

For extended validation and supplying schema data, use the `Body` function:

```python
from starlite import Body, post

from my_app.models import User


@post(path="/user")
async def create_user(
    data: User = Body(title="Create User", description="Create a new user.")
) -> User:
    ...
```

The `Body` function is very similar to the [Parameter function](3-parameters#the-parameter-function), and it receives the following
kwargs:

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

## URL Encoded Form Data

To access _url encoded_ form data, i.e. data sent with an `application/x-www-form-urlencoded` Content-Type header, you
need to use `Body` and specify `RequestEncodingType.URL_ENCODED` as the `media_type` kwarg:

```python
from starlite import Body, post, RequestEncodingType

from my_app.models import User


@post(path="/user")
async def create_user(
    data: User = Body(media_type=RequestEncodingType.URL_ENCODED),
) -> User:
    ...
```

The above ensures that Starlite will inject data using the request.form() method rather than request.json(). It also
causes the generated OpenAPI schema to use the correct media type.

<!-- prettier-ignore -->
!!! important
    url encoded data is inherently less versatile than JSON data - for example, it cannot handle complex
    dictionaries and deeply nested data. It should only be used for simple data structures, e.g. frontend forms.

## MultiPart Form Data

Multipart formdata supports complex formdata including file uploads.

You can access data uploaded using a request with a `multipart/form-data` Content-Type header by specifying it in
the `Body` function:

```python
from starlite import Body, post, RequestEncodingType

from my_app.models import User


@post(path="/user")
async def create_user(
    data: User = Body(media_type=RequestEncodingType.MULTI_PART),
) -> User:
    ...
```

### Accessing Files

In case of files uploaded, Starlette transforms the results into an instance
of [starlette.datastructures.UploadFile](https://www.starlette.io/requests/#request-files), which offer a convenient
interface for working with files. Therefore, you need to type your file uploads accordingly.

To access a single file simply type `data` as `UploadFile`:

```python
from starlette.datastructures import UploadFile
from starlite import Body, post, RequestEncodingType


@post(path="/file-upload")
async def handle_file_upload(
    data: UploadFile = Body(media_type=RequestEncodingType.MULTI_PART),
) -> None:
    ...
```

To access multiple files with known filenames, you can use a pydantic model:

```python title="my_app/models.py"
from pydantic import BaseModel
from starlette.datastructures import UploadFile


class FormData(BaseModel):
    cv: UploadFile
    image: UploadFile

    class Config:
        arbitrary_types_allowed = True
```

```python
from starlite import Body, post, RequestEncodingType

from my_app.models import FormData


@post(path="/file-upload")
async def handle_file_upload(
    data: FormData = Body(media_type=RequestEncodingType.MULTI_PART),
) -> None:
    ...
```

If you do not care about parsing and validation and only want to access the form data as a dictionary, you can do this:

```python
from starlette.datastructures import UploadFile
from starlite import Body, post, RequestEncodingType
from typing import Dict


@post(path="/file-upload")
async def handle_file_upload(
    data: Dict[str, UploadFile] = Body(media_type=RequestEncodingType.MULTI_PART)
) -> None:
    ...
```

Finally, if you do not know the filenames are do not care about them, you can get the files as a list:

```python
from starlette.datastructures import UploadFile
from starlite import Body, post, RequestEncodingType
from typing import List


@post(path="/file-upload")
async def handle_file_upload(
    data: List[UploadFile] = Body(media_type=RequestEncodingType.MULTI_PART),
) -> None:
    ...
```
