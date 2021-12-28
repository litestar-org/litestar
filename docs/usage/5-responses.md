# Responses

When you return a value from a route handler function, Starlite takes the value and passes it to the constructor of the
Starlite `Response` class (_starlite.response.Response_), as the response's `content` kwarg. It also sets the
response's `status_code` and `media_type` kwargs based on either what was defined in the route handler decorator or
default values.

For example, lets assume we have a model named `Resource` which we persist using some orm abstracted into a repository
pattern:

```python title="my_api/models/resource.py"
from pydantic import BaseModel


class Resource(BaseModel):
    id: int
    name: str
```

We have a route handler that takes a `resource_id` kwarg, passed as a path parameter, which retrieves the persisted
instance. After which the value is returned from the route handler function:

```python
from starlite import get

from my_api.models import Resource
from my_api.db import ResourceRepository


@get(path="/resources/{resource_id:int}")
async def retrieve_resource(resource_id: int) -> Resource:
    resource = await ResourceRepository.find(id=resource_id)
    return resource
```

When the `retrieve_resource` handler is called and returns, Starlite will use the return value to create a `Response`
with a `status_code` of `HTTP_200_OK`, which is the default for GET, and a `media_type` of `MediaType.JSON`, which is
the default media type. As a result the return value, which is a pydantic model, will be serialized into JSON, and the
response's _Content-Type_ header will be set to "application/json".

## Status Codes

You can specify a _status_code_ to set for the response as a decorator kwarg:

```python
from starlite import get
from starlette.status import HTTP_202_ACCEPTED

from my_api.models import Resource
from my_api.db import ResourceRepository


@get(path="/resources/{resource_id:int}", status_code=HTTP_202_ACCEPTED)
async def retrieve_resource(resource_id: int) -> Resource:
    resource = await ResourceRepository.find(id=resource_id)
    return resource
```

Setting the `status_code` kwarg is optional for _delete_, _get_, _patch_, _post_ and _put_ decorators, and also for
the _route_ decorators when only setting a single `http_method`. If not set by the user, the following defaults will be
used:

* POST: 201 (Created)
* DELETE: 204 (No Content)
* GET, PATCH, PUT: 200 (Ok)

Please note that when designating a function as a handler for multiple http methods, a `status_code` kwarg must be
passed or an exception will be raised.

Also note that the default for `delete` is no content because by default it is assumed that delete operations return no
data. This though might not be the case in your implementation - so take care of setting it as you see fit.

## Media Type

As mentioned above, the default media type is `MediaType.JSON`. `MediaType` here is a Starlite enum which is used for
convenience - you can pass a string value as well but should ensure that it is a legitimate value according to the
receiver / OpenAPI specs. This enum has 3 members, each correlating with a specific `Content-Type` header:

* MediaType.JSON: application/json
* MediaType.TEXT: text/plain
* MediaType.HTML: text/html

The return value of the handler should correlate with the correct _media_type_ (see below):

### Text Responses

For `MediaType.TEXT`, route handlers should return a value of type **string** or **bytes**:

```python
from starlite import get, MediaType


@get(path="/health-check", media_type=MediaType.TEXT)
def health_check() -> str:
    return "healthy"
```

### HTML Responses

For `MediaType.HTML`, route handlers should return a value of type **string** or **bytes** that contains HTML:

```python
from starlite import get, MediaType


@get(path="/page", media_type=MediaType.HTML)
def health_check() -> str:
    return """
    <html>
        <body>
            <div>
                <span>Hello World!</span>
            </div>
        </body>
    </html>
    """
```

Note: It's a good idea to use a templating engine for more complex HTML responses and to write the template itself in a
separate file rather than a string.

### JSON Responses

As previously mentioned, the default _media_type_ is `MediaType.JSON`, which supports the following values:

* dictionaries
* dataclasses from the standard library
* pydantic dataclasses
* pydantic models
* models from libraries that extend pydantic models
* numpy ndarray
* lists containing any of the above elements

Since Starlite uses the excellent (and super-fast!) [orjson](https://github.com/ijl/orjson#numpy) library to handle
JSON (also in requests), you can use the following values as part of your responses without issue:

* all UUIDs
* datetime classes
* numpy primitives and objects (see [orjson docs](https://github.com/ijl/orjson#numpy))

If you need to return other values and would like to extend serialization you can do
this [using Custom Responses](#using-custom-responses).

## Response Types

Not all responses can be inferred using the `media_type` kwarg, and for these types of responses Starlite relies on
special wrapper classes.

### Redirect Responses

Redirect responses are [special HTTP responses](https://developer.mozilla.org/en-US/docs/Web/HTTP/Redirections) with a
status code in the 30x range. In Starlite, a redirect response looks like this:

```python
from starlette.status import HTTP_307_TEMPORARY_REDIRECT
from starlite import get, Redirect


@get(path="/some-path", status_code=HTTP_307_TEMPORARY_REDIRECT)
def redirect() -> Redirect:
    # do some stuff here
    # ...
    # finally return redirect
    return Redirect(path="/other-path")
```

To return a redirect response you should do the following:

1. set an appropriate status code for the route handler (301, 302, 303, 307, 308)
2. annotate the return value of the route handler as returning `Redirect`
3. return an instance of the `Redirect` class with the desired redirect path

### File Responses

File responses send a file:

```python
from pathlib import Path
from starlite import get, File


@get(path="/file-download")
def handle_file_download() -> File:
    return File(
        path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
        filename="repost.pdf",
    )
```

The File class expects two kwargs:

* `path`: path of the file to download.
* `filename`: the filename to set in the
  response [Content-Disposition](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Disposition)
  attachment.

!!! important
    When a route handler's return value is annotated with `File`, the default `media_type` for the
    route_handler is switched from `MediaType.JSON` to `MediaType.TEXT` (i.e. "text/plain"). If the file being sent has
    an [IANA media type](https://developer.mozilla.org/en-US/docs/Web/HTTP/Basics_of_HTTP/MIME_types), you should set it as
    the value for `media_type` instead.

For example:

```python
from pathlib import Path
from starlite import get, File


@get(path="/file-download", media_type="application/pdf")
def handle_file_download() -> File:
    return File(
        path=Path(Path(__file__).resolve().parent, "report").with_suffix(".pdf"),
        filename="repost.pdf",
    )
```

### Streaming Responses

To return a streaming response use the `Stream` class:

```python
from asyncio import sleep
from starlite import get, Stream
from datetime import datetime
from orjson import dumps


async def my_iterator() -> bytes:
    while True:
        await sleep(0.01)
        yield dumps({"current_time": datetime.now()})


@get(path="/time")
def stream_time() -> Stream:
    return Stream(iterator=my_iterator)
```

The Stream class receives a single required kwarg - `iterator`, which should be either a sync or an async iterator.

## Customizing Response Objects

You can also return an instance of any Starlette response class or a subclass of it directly from a route handler. You
should do this only if you have a use case for these specific response types and otherwise

## Using Custom Responses

You can use a subclass of `starlite.responses.Response` and specify it as the response class using the `response_class`
kwarg.

For example, lets say we want to handle subclasses of `Document` from the `elasticsearch_dsl` package as shown below:

```python
from elasticsearch_dsl import Document, Integer, Keyword


class MyDocument(Document):
    name = Keyword()
    level = Integer()
    type = Keyword()
```

It would be best if we had a generic response class that was able to handle all `Document` subclasses. Luckily,
the `Document` model already comes with a `to_dict` method, which makes our lives a bit simpler:

```python
from typing import Any, Dict

from elasticsearch_dsl import Document
from starlite import Response


class DocumentResponse(Response):
    def serializer(self, value: Any) -> Dict[str, Any]:
        if isinstance(value, Document):
            return value.to_dict()
        return super().serializer(value)
```

We can now use this in our route handler:

```python
from elasticsearch_dsl import Document
from starlite import get

from my_app.responses import DocumentResponse


@get(path="/document", response_class=DocumentResponse)
def get_document() -> Document:
    ...
```

You can specify the response class to use at all levels of your application. On specific route handlers, as above, on a
Controller, on Router or even on the app instance itself:

```python
from starlite import Controller, Starlite, Router

from my_app.responses import DocumentResponse


# controller
class MyController(Controller):
    path = "..."
    response_class = DocumentResponse


# router
my_router = Router(path="...", route_handlers=[...], response_class=DocumentResponse)

# app
my_app = Starlite(route_handlers=[...], response_class=DocumentResponse)
```

When you specify a response_class in multiple places, the closest layer to the response handler will take precedence.
That is, the `response_class` specified on the route handler takes precedence over the one specified on the controller
or router, which in turn take precedence over the one specified on the app level. You can therefore easily override
response classes as needed.

## Returning Responses Directly

You can return an instance of any Starlette response, including the Starlite `Response` and subclasses thereof from a route handler function:

```python
from starlite import get
from starlette.responses import Response


@get(path="/")
def my_route_handler() -> Response:
    return Response(...)
```

OR

```python
from starlite import get, Response


@get(path="/")
def my_route_handler() -> Response:
    return Response(...)
```

!!! important
    If you return a response directly the OpenAPI schema generation will not be able to properly annotate the response.

## Response Headers

WIP
