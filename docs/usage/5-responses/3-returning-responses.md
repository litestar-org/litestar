# Returning Responses

While the default response handling fits most use cases, in some cases you need to be able to return a response instance
directly.

Starlite allows you to return any class inheriting from the `starlette.responses.Response` class. Thus, the below
example will work perfectly fine:

```python
from starlite import get
from starlette.responses import Response
from starlette.status import HTTP_202_ACCEPTED


@get("/")
def my_route_handler() -> Response:
    response = Response(
        content="123", headers={"MY-HEADER": "123"}, status_code=HTTP_202_ACCEPTED
    )
    response.set_cookie("my_cookie", value="abc")
    return response
```

The caveat of using a Starlette response though is that Starlite will not be able to infer the OpenAPI documentation.

## Annotated Responses

To solve this issue, use you can use the `starlite.response.Response` class which supports type annotations:

```python
from pydantic import BaseModel
from starlite import Response, get
from starlite.datastructures import Cookie


class Resource(BaseModel):
    id: int
    name: str


@get("/resources")
def retrieve_resource() -> Response[Resource]:
    return Response(
        Resource(
            id=1,
            name="my resource",
            headers={"MY-HEADER": "xyz"},
            cookies=[Cookie("my-cookie", value="abc")],
        )
    )
```

As you can see above, the `starlite.response.Response` class accepts a generic argument - in this case the pydantic
model `Resource`. This allows Starlite to infer from the Response type the correct typing for OpenAPI generation.
