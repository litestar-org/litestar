# URL Encoded Form Data

To access data sent as [url-encoded form data](https://developer.mozilla.org/en-US/docs/Web/HTTP/Methods/POST),
i.e. `application/x-www-form-urlencoded` Content-Type header, use `Body` and specify `RequestEncodingType.URL_ENCODED` as
the `media_type`:

```python
from starlite import Body, post, RequestEncodingType
from pydantic import BaseModel


class User(BaseModel):
    ...


@post(path="/user")
async def create_user(
    data: User = Body(media_type=RequestEncodingType.URL_ENCODED),
) -> User:
    ...
```

The above ensures that Starlite will inject data using the request.form() method rather than request.json() and set the correct media-type in the OpenAPI schema.

<!-- prettier-ignore -->
!!! important
    url encoded data is inherently less versatile than JSON data - for example, it cannot handle complex
    dictionaries and deeply nested data. It should only be used for simple data structures.
