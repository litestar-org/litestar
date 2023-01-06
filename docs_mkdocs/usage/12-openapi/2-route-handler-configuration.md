# Route Handler OpenAPI Configuration

By default, an [operation](https://spec.openapis.org/oas/latest.html#operation-object) schema is generated for all route
handlers. You can omit a route handler from the schema by setting `include_in_schema=False`:

```python
from starlite import get


@get(path="/some-path", include_in_schema=False)
def my_route_handler() -> None:
    ...
```

You can also modify the generated schema for the route handler using the following kwargs:

- `tags`: A list of strings that correlate to
  the [tag specification](https://spec.openapis.org/oas/latest.html#tag-object).
- `security`: A list of dictionaries that correlate to
  the [security requirements specification](https://spec.openapis.org/oas/latest.html#securityRequirementObject). The
  values for this key are string keyed dictionaries with the values being a list of objects.
- `summary`: Text used for the route's schema _summary_ section.
- `description`: Text used for the route's schema _description_ section.
- `response_description`: Text used for the route's response schema _description_ section.
- `operation_id`: An identifier used for the route's schema _operationId_. Defaults to the `__name__` attribute of the
  wrapped function.
- `deprecated`: A boolean dictating whether this route should be marked as deprecated in the OpenAPI schema. Defaults
  to `False`.
- `raises`: A list of exception classes extending from `starlite.HttpException`. This list should describe all
  exceptions raised within the route handler's function/method. The Starlite `ValidationException` will be added
  automatically for the schema if any validation is involved (e.g. there are parameters specified in the
  method/function).
- `responses`: A dictionary of additional status codes and a description of their expected content.
    The expected content should be based on a Pydantic model describing its structure. It can also include
    a description and the expected media type. For example:

!!! note
    `operation_id` will be prefixed with the method name when function is decorated with `HTTPRouteHandler` and multiple `http_method`. Will also be prefixed with path strings used in `Routers` and `Controllers` to make sure id is unique.

```python
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from starlite import ResponseSpec, get


class Item(BaseModel):
    ...


class ItemNotFound(BaseModel):
    was_removed: bool
    removed_at: Optional[datetime]


@get(
    path="/items/{pk:int}",
    responses={
        404: ResponseSpec(
            model=ItemNotFound, description="Item was removed or not found"
        )
    },
)
def retrieve_item(pk: int) -> Item:
    ...
```

You can also specify `security` and `tags` on higher level of the application, e.g. on a controller, router or the app instance itself. For example:

```python
from starlite import Starlite, OpenAPIConfig, get
from pydantic_openapi_schema.v3_1_0 import Components, SecurityScheme, Tag


@get(
    "/public",
    tags=["public"],
    security=[{}],  # this endpoint is marked as having optional security
)
def public_path_handler() -> dict[str, str]:
    return {"hello": "world"}


@get("/other", tags=["internal"], security=[{"apiKey": []}])
def internal_path_handler() -> None:
    ...


app = Starlite(
    route_handlers=[public_path_handler, internal_path_handler],
    openapi_config=OpenAPIConfig(
        title="my api",
        version="1.0.0",
        tags=[
            Tag(name="public", description="This endpoint is for external users"),
            Tag(name="internal", description="This endpoint is for internal users"),
        ],
        security=[{"BearerToken": []}],
        components=Components(
            securitySchemes={
                "BearerToken": SecurityScheme(
                    type="http",
                    scheme="bearer",
                )
            },
        ),
    ),
)
```
