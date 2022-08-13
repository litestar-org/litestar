# MultiPart Form Data

Multipart formdata supports complex formdata including file uploads.

You can access data uploaded using a request with a `multipart/form-data` Content-Type header by specifying it in
the `Body` function:

```python
from starlite import Body, post, RequestEncodingType
from pydantic import BaseModel


class User(BaseModel):
    ...


@post(path="/user")
async def create_user(
    data: User = Body(media_type=RequestEncodingType.MULTI_PART),
) -> User:
    ...
```

## Accessing Files

In case of files uploaded, Starlette transforms the results into an instance
of [starlette.datastructures.UploadFile](https://www.starlette.io/requests/#request-files), which offer a convenient
interface for working with files. Therefore, you need to type your file uploads accordingly.

To access a single file simply type `data` as `UploadFile`:

```python
from starlite import Body, UploadFile, post, RequestEncodingType


@post(path="/file-upload")
async def handle_file_upload(
    data: UploadFile = Body(media_type=RequestEncodingType.MULTI_PART),
) -> None:
    ...
```

To access multiple files with known filenames, you can use a pydantic model:

```python
from pydantic import BaseModel
from starlette.datastructures import UploadFile
from starlite import Body, post, RequestEncodingType


class FormData(BaseModel):
    cv: UploadFile
    image: UploadFile

    class Config:
        arbitrary_types_allowed = True


@post(path="/file-upload")
async def handle_file_upload(
    data: FormData = Body(media_type=RequestEncodingType.MULTI_PART),
) -> None:
    ...
```

If you do not care about parsing and validation and only want to access the form data as a dictionary, you can use a `dict` instead:

```python
from starlette.datastructures import UploadFile
from starlite import Body, post, RequestEncodingType


@post(path="/file-upload")
async def handle_file_upload(
    data: dict[str, UploadFile] = Body(media_type=RequestEncodingType.MULTI_PART)
) -> None:
    ...
```

Finally, you can also access the files as a list without the filenames:

```python
from starlette.datastructures import UploadFile
from starlite import Body, post, RequestEncodingType


@post(path="/file-upload")
async def handle_file_upload(
    data: list[UploadFile] = Body(media_type=RequestEncodingType.MULTI_PART),
) -> None:
    ...
```
