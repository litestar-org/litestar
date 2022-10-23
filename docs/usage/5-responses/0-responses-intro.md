# HTTP Responses

Starlite allows for several ways in which HTTP responses can be specified and handled, each fitting a different use
case. The base pattern though is straightforward - simply return a value from a route handler function and let
Starlite take care of the rest:

```python
from pydantic import BaseModel
from starlite import get


class Resource(BaseModel):
    id: int
    name: str


@get("/resources")
def retrieve_resource() -> Resource:
    return Resource(id=1, name="my resource")
```

In the example above, the route handler function returns an instance of the `Resource` pydantic class. This value will
then be used by Starlite to construct an instance of the [`Response`][starlite.response.Response]
class using defaults values: the response status code will be set to `200` and it's `Content-Type` header will be set
to `application/json`. The `Resource` instance will be serialized into JSON and set as the response body.
