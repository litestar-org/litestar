# OpenAPI

Starlite has first class OpenAPI support offering the following features:

1. extensive OpenAPI 3.1.0 spec generation
2. integrated [Redoc](https://github.com/Redocly/redoc) UI

## Spec Generation

Spec Generation utilizes the excellent [openapi-schema-pydantic](https://github.com/kuimono/openapi-schema-pydantic)
library, which offers a complete implementation of the OpenAPI specs as pydantic models. Starlite generates OpenAPI
specs version [3.1.0 - the latest version of the specification](https://spec.openapis.org/oas/latest.html).

### App Level Configuration

OpenAPI schema generation is enabled by default. To configure it you can pass an instance
of `starlite.config.OpenAPIConfig` to the Starlite constructor using the `openapi_config` kwarg:

```python title="my_app/main.py"
from starlite import Starlite, OpenAPIConfig

app = Starlite(
    route_handlers=[...], openapi_config=OpenAPIConfig(title="My API", version="1.0.0")
)
```

Aside from `title` and `version`, both of which are **required** kwargs, you can pass the following optional kwargs:

- `create_examples`: Boolean flag dictating whether examples will be auto-generated using
  the [pydantic-factories](https://github.com/starlite-api/pydantic-factories) library. Defaults to `False`.
- `openapi_controller`: The controller class to use for the openapi to generate the openapi related routes. Must be a
  subclass of [the openapi controller class](#the-openapi-controller).
- `contact`: An instance of the `Contact` model.
- `description`: Description text.
- `external_docs`: An instance of the `ExternalDocumentation` model.
- `license`: An instance of the `License` model.
- `security`: An instance of the `SecurityRequirement` model.
- `servers`: A list of `Server` model instances. defaults to `[Server("/")]`
- `summary`: Summary text.
- `tags`: A list of `Tag` model instances.
- `terms_of_service`: A url to a page containing the terms of service.
- `webhooks`: A string keyed dictionary of `PathItem` model instances.

!!! note
    All models listed above are exported from [openapi-schema-pydantic](https://github.com/kuimono/openapi-schema-pydantic)
    rather than Starlite.

#### Disable Schema Generation

If you wish to disable schema generation and not include the schema endpoints in your API, simply pass `None` as the
value for `openapi_config`:

```python title="my_app/main.py"
from starlite import Starlite, OpenAPIConfig

app = Starlite(
    route_handlers=[...], openapi_config=None
)
```


### Route Handler Configuration

By default, an [operation](https://spec.openapis.org/oas/latest.html#operation-object) schema is generated for all route
handlers. You can omit a route handler from the schema by setting `include_in_schema` to `False`:

```python
from starlite import get


@get(path="/some-path", include_in_schema=False)
def my_route_handler() -> None:
    ...
```

You can also affect the schema by enriching and/or modifying it using the following kwargs:

- `tags`: a list of openapi-pydantic `Tag` models, which correlate to
  the [tag specification](https://spec.openapis.org/oas/latest.html#tag-object).
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

## Accessing the OpenAPI Schema

The generated schema is an instance of the `OpenAPI` pydantic model, and you can access it in any route handler like so:

```python
from starlite import Request, get


@get(path="/")
def my_route_handler(request: Request) -> None:
    schema = request.app.openapi_schema
    ...
```

### The OpenAPI Controller

Starlite includes a pre-configured controller called `OpenAPIController` which exposes three endpoints:

1. `/schema/openapi.yaml`, allowing for download of the OpenAPI schema as YAML, using the `application/vnd.oai.openapi`
   Content-Type.
2. `/schema/openapi.json`, allowing for download of the OpenAPI schema as JSON, using
   the `application/vnd.oai.openapi+json` Content-Type.
3. `/schema/redoc`, which serves a [Redoc](https://github.com/Redocly/redoc) UI static website for the OpenAPI docs.

If you would like to modify the endpoints, add new endpoints, change the styling of redoc etc., you can subclass the
`OpenAPIController` and then pass your subclass to the `OpenAPIConfig`.

For example, lets say we wanted to change the base path from "/schema" to "/api-docs":

```python title="my_app/openapi.py"
from starlite import OpenAPIController


class MyOpenAPIController(OpenAPIController):
    path = "/api-docs"
```

We would then use the subclassed controller like so:

```python
from starlite import Starlite, OpenAPIConfig

from my_app.openapi import MyOpenAPIController

app = Starlite(
    route_handlers=[...],
    openapi_config=OpenAPIConfig(openapI_controller=MyOpenAPIController),
)
```
