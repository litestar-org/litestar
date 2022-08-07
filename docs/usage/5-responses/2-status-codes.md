# Status Codes

You can control the response `status_code` by setting the corresponding kwarg to the desired value:

```python
from pydantic import BaseModel
from starlite import get
from starlette.status import HTTP_202_ACCEPTED


class Resource(BaseModel):
    id: int
    name: str


@get("/resources", status_code=HTTP_202_ACCEPTED)
def retrieve_resource() -> Resource:
    return Resource(id=1, name="my resource")
```

If `status_code` is not set by the user, the following defaults are used:

- POST: 201 (Created)
- DELETE: 204 (No Content)
- GET, PATCH, PUT: 200 (Ok)

<!-- prettier-ignore -->
!!! note
    When using the `route` decorator with multiple http methods, the default status code is `200`.

<!-- prettier-ignore -->
!!! note
    The default for `delete` is `204` because by default it is assumed that delete operations return no data.
    This though might not be the case in your implementation - so take care of setting it as you see fit.

<!-- prettier-ignore -->
!!! tip
    While you can write integers as the value for `status_code`, e.g. `200`, its best practice to use constants (also in
    tests). Starlette includes easy to use statuses that are exported from `starlette.status`, e.g. `HTTP_200_OK`
    and `HTTP_201_CREATED`. Another option is the `http.HTTPStatus`enum from the standard library, which also offers
    extra functionality. For this see [the standard library documentation](https://docs.python.org/3/library/http.html#http.HTTPStatus).
