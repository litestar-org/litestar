# Response Headers

Starlite allows you to define response headers by using the `response_headers` kwarg. This kwarg is
available on all layers of the app - individual route handlers, controllers, routers and the app
itself:

```python
from starlite import Starlite, Router, Controller, MediaType, get
from starlite.datastructures import ResponseHeader


class MyController(Controller):
    path = "/controller-path"
    response_headers = {
        "controller-level-header": ResponseHeader(
            value="controller header", description="controller level header"
        )
    }

    @get(
        path="/",
        response_headers={
            "my-local-header": ResponseHeader(
                value="local header", description="local level header"
            )
        },
        media_type=MediaType.TEXT,
    )
    def my_route_handler(self) -> str:
        return "hello world"


router = Router(
    path="/router-path",
    route_handlers=[MyController],
    response_headers={
        "router-level-header": ResponseHeader(
            value="router header", description="router level header"
        )
    },
)

app = Starlite(
    route_handlers=[router],
    response_headers={
        "app-level-header": ResponseHeader(
            value="app header", description="app level header"
        )
    },
)
```

In the above example the response returned from `my_route_handler` will have headers set from each layer of the
application using the given key+value combinations. I.e. it will be a dictionary equal to this:

```json
{
  "my-local-header": "local header",
  "controller-level-header": "controller header",
  "router-level-header": "router header",
  "app-level-header": "app header"
}
```

The respective descriptions will be used for the OpenAPI documentation.

## Dynamic Headers

The above detailed scheme works great for statically configured headers, but how would you go about handling dynamically
setting headers? Starlite allows you to set headers dynamically in several ways and below we will detail the two
primary patterns.

### Setting Response Headers Using Annotated Responses

We can simply return a response instance directly from the route handler and set the headers dictionary manually
as you see fit, e.g.:

```python
from pydantic import BaseModel
from starlette.status import HTTP_200_OK
from starlite import Response, get
from starlite.datastructures import ResponseHeader
from starlite.enums import MediaType
from random import randint


class Resource(BaseModel):
    id: int
    name: str


@get(
    "/resources",
    response_headers={
        "Random-Header": ResponseHeader(
            description="a random number in the range 1 - 100", documentation_only=True
        )
    },
)
def retrieve_resource() -> Response[Resource]:
    return Response(
        Resource(
            id=1,
            name="my resource",
        ),
        headers={"Random-Header": str(randint(1, 100))},
        media_type=MediaType.JSON,
        status_code=HTTP_200_OK,
    )
```

In the above we use the `response_headers` kwarg to pass the `name` and `description` parameters for the `Random-Header`
to the OpenAPI documentation, but we set the value dynamically in as part of
the [annotated response](3-returning-responses.md#annotated-responses) we return. To this end we do not set a `value`
for it and we designate it as `documentation_only=True`.

### Setting Response Headers Using the After Request Hook

An alternative pattern would be to use an [after request handler](../13-lifecycle-hooks.md#after-request). We can define
the handler on different layers of the application as explained in the pertinent docs. We should take care to document
the headers on the corresponding layer:

```python
from random import randint

from pydantic import BaseModel
from starlette.status import HTTP_200_OK
from starlite import Response, Router, get
from starlite.datastructures import ResponseHeader
from starlite.enums import MediaType


class Resource(BaseModel):
    id: int
    name: str


@get(
    "/resources",
    response_headers={
        "Random-Header": ResponseHeader(
            description="a random number in the range 100 - 1000",
            documentation_only=True,
        )
    },
)
def retrieve_resource() -> Response[Resource]:
    return Response(
        Resource(
            id=1,
            name="my resource",
        ),
        headers={"Random-Header": str(randint(100, 1000))},
        media_type=MediaType.JSON,
        status_code=HTTP_200_OK,
    )


def after_request_handler(response: Response) -> Response:
    response.headers.update({"Random-Header": str(randint(1, 100))})
    return response


router = Router(
    path="/router-path",
    route_handlers=[retrieve_resource],
    after_request=after_request_handler,
    response_headers={
        "Random-Header": ResponseHeader(
            description="a random number in the range 1 - 100", documentation_only=True
        )
    },
)
```

In the above we set the response header using an `after_request_handler` function on the router level. Because the
handler function is applied on the router, we also set the documentation for it on the router.

We can use this pattern to fine-tune the OpenAPI documentation more granularly by overriding header specification as
required. For example, lets say we have a router level header being set and a local header with the same key but a
different value range:

```python
from pydantic import BaseModel
from starlite import Router, Response, get
from starlite.datastructures import ResponseHeader
from random import randint


class Resource(BaseModel):
    id: int
    name: str


@get(
    "/resources",
    response_headers={
        "Random-Header": ResponseHeader(
            description="a random number in the range 100 - 1000",
            documentation_only=True,
        )
    },
)
def retrieve_resource() -> Response[Resource]:
    return Response(
        Resource(
            id=1,
            name="my resource",
        ),
        headers={"Random-Header": str(randint(100, 1000))},
    )


def after_request_handler(response: Response) -> Response:
    response.headers.update({"Random-Header": str(randint(1, 100))})
    return response


router = Router(
    route_handlers=[retrieve_resource],
    after_request=after_request_handler,
    response_headers={
        "Random-Header": ResponseHeader(
            description="a random number in the range 1 - 100", documentation_only=True
        )
    },
)

# ...
```
