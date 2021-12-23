# Responses

There are two ways to return responses from route handlers:

1. return a serializable value from the handler function and let Starlite take care of the response for you.
2. return an instance of a Starlette `Response` or any of its subclasses.

We'll discuss the use cases for these two scenarios in this order

## Returning Values from Route Handlers

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

The return value of the handler should correlate with the correct _media_type_.

For `MediaType.TEXT` the value should be of type **string** or **bytes**:

```python
from starlite import get, MediaType


@get(path="/health-check", media_type=MediaType.TEXT)
def health_check() -> str:
    return "healthy"
```

For `MediaType.HTML` the value should be a **string** or **bytes** that contain valid HTML; and for `MediaType.HTML`

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

For `MediaType.JSON` you should return any of the following supported value types:

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

The return value of the handler will be passed the Starlite `Response` constructor alongside the the media-type defined
for the route handler, which is by default `MediaType.JSON` (i.e. "application/json"). Because in this instance the
value is a pydantic model - which can be serialized by the response, this

Based on the media-type, the Starlite will determine that this value is an instance of a pydantic model, and thus
serialize it correctly using the pydantic.json() method. This also works for serializing list of pydantic models.

Starlite supports serializing into json all uses the excellent and very fast
library [orjson](https://github.com/ijl/orjson) to serializing the following value types into JSON by default:

1. pydantic models
2. dataclasses (both pydantic and standard library)
3. vanilla python dataclasses
4. all python primitives
5. datetime
6. UUIDs

Note: If you need to return other values that are not supported by orjson, see [Using Custom Responses](#using-custom-responses) at the bottom of this page.

##

## Using Custom Responses
