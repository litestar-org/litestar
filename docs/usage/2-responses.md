# Responses

When you return a value from a route handler function, Starlite takes the value and passes it to the constructor of the
Starlite `Response` class (_starlite.response.Response_), as the response's `content` kwarg. It also sets the
response's `status_code` and `media_type` kwargs based on either what was defined in the route handler decorator or
default values.

For example, lets assume we have a model named `Resource` which we persist using some orm abstracted into a repository
pattern:

```python
# my_api/models/resource.py

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

### Status Codes

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

### Media Type

As mentioned above, the default media type is `MediaType.JSON`. `MediaType` here is a Starlite enum which is used for
convenience - you can pass a string value as well but should ensure that it is a legitimate value according to the
receiver / OpenAPI specs. This enum has 3 members, each correlating with a specific `Content-Type` header:

* MediaType.JSON: application/json
* MediaType.TEXT: text/plain
* MediaType.HTML: text/html

The return value of the handler should correlate with the correct _media_type_:

#### Text Responses

For `MediaType.TEXT`, route handlers should return a value of type **string** or **bytes**:

```python
from starlite import get, MediaType


@get(path="/health-check", media_type=MediaType.TEXT)
def health_check() -> str:
    return "healthy"
```

#### HTML Responses

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

Note: there is no validation involved in Starlite, so you should make sure to return valid HTML by whatever means you
see fit. It's a good idea to use a templating engine for more complex HTML responses and to write the template
itself in a separate file rather than a string.

#### JSON Responses

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

If you need to return other values and would like to extend serialization you can do this [using Custom Responses](#using-custom-responses).

### Returning Responses

You can also return an instance of any Starlette response class or a subclass of it directly from a route handler. You
should do this only if you have a use case for these specific response types and otherwise

## Using Custom Responses
