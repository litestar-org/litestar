# OpenAPI

Starlite has first class OpenAPI support offering the following features:

1. extensive OpenAPI spec generation
2. integrated [Redoc](https://github.com/Redocly/redoc) UI

## Spec Generation

Spec Generation utilizes the excellent [openapi-schema-pydantic](https://github.com/kuimono/openapi-schema-pydantic)
library, which offers a complete implementation of the OpenAPI specs as pydantic models. Starlite generates OpenAPI
specs version [3.1.0 - the latest version of the specification](https://spec.openapis.org/oas/latest.html).

### App Level Configuration

To enable OpenAPI schema generation you need to pass an instance of `OpenAPIConfig` to the Starlite constructor using
the `openapi_config` kwarg:

```python
from starlite import Starlite, OpenAPIConfig

app = Starlite(
    route_handlers=[...], openapi_config=OpenAPIConfig(title="My API", version="1.0.0")
)
```

Aside from `title` and `version`, both of which are **required** kwargs, you can pass the following optional kwargs:

* `create_examples`: Boolean flag dictating whether examples will be auto-generated using
  the [pydantic-factories](https://github.com/starlite-api/pydantic-factories) library. Defaults to `False`.
* `contact`: An instance of the `Contact` model.
* `description`: Description text.
* `external_docs`: An instance of the `ExternalDocumentation` model.
* `license`: An instance of the `License` model.
* `security`: An instance of the `SecurityRequirement` model.
* `servers`: A list of `Server` model instances. defaults to `[Server("/")]`
* `summary`: Summary text.
* `tags`: A list of `Tag` model instances.
* `terms_of_service`: A url to a page containing the terms of service.
* `webhooks`: A string keyed dictionary of `PathItem` model instances.

!!! note
    All models listed above are exported
    from [openapi-schema-pydantic](https://github.com/kuimono/openapi-schema-pydantic)
    rather than Starlite.

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
  automatically for the schema if any validation is involved (e.g. there are parameters specified in the method/function).

## Accessing the Schema

Once you enable OpenAPI schema generation by passing a config object to the Starlite constructor, the generated schema
will become accessible in any route handler:

```python
from starlite import Request, get


@get(path="/")
def my_route_handler(request: Request) -> None:
    schema = request.app.openapi_schema
    ...
```

The schema in the above is an instance of the `OpenAPI` pydantic model, and you can interact with it as you would with
any other pydantic model

### The OpenAPI Controller

Starlite includes a pre-configured controller called `OpenAPIController` which exposes two endpoints:

1. a schema download endpoint with the default path - `/schema`
2. an HTML endpoint that serves a Redoc UI for the schema with the default path - `/schema/redoc`

To enable this controller simply add it to the app route handlers or a router, e.g.:

```python
from starlite import OpenAPIController, Starlite

app = Starlite(route_handlers=[OpenAPIController])
```

The defaults for this controller are:

1. path = `/schema`
2. schema is sent using the `application/vnd.oai.openapi+json` Content-Type header
3. there is no styling of Redoc and no favicon for it

For example, lets say we wanted to serve the schema using the `application/vnd.oai.openapi` Content-Type, which is the
convention for YAML, rather than using JSON. In this case we would do this:

```python title="my_app/openapi.py"
from openapi_schema_pydantic import OpenAPI
from starlite import OpenAPIController, OpenAPIMediaType, Request, get


class MyOpenAPIController(OpenAPIController):
    @get(media_type=OpenAPIMediaType.OPENAPI_YAML, include_in_schema=False)
    def retrieve_schema(self, request: Request) -> OpenAPI:
        """Returns the openapi schema"""
        return self.schema_from_request(request)
```

And then we would use this controller our app instead:

```python
from starlite import Starlite

from my_app.openapi import MyOpenAPIController

app = Starlite(route_handlers=[MyOpenAPIController])
```

### Redoc

As mentioned previously the Starlite `OpenAPIController` comes with a Redoc UI endpoint. Once you enable the controller
you can access the endpoint at `/schema/redoc` - by default. You can of course modify this path as you see fit.

Redoc is served using a basic HTML template with no additional styling and no favicon. If you want to change this, you
can easily do so by subclassing the controller and modifying the template.
