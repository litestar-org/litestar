# The OpenAPIController

Starlite includes an [OpenAPIController][starlite.openapi.controller.OpenAPIController] class that is used as the
default controller in the [OpenAPIConfig](1-schema-generation.md).

This controller exposes the following endpoints:

- `/schema/openapi.yaml`: allowing for download of the OpenAPI schema as YAML.
- `/schema/openapi.json`: allowing for download of the OpenAPI schema as JSON.
- `/schema/redoc`: which serve the docs using [Redoc](https://github.com/Redocly/redoc).
- `/schema/swagger`: which serves the docs using[Swagger-UI](https://swagger.io/docs/open-source-tools/swagger-ui/).
- `/schema/elements`: which serves the docs using [Stoplight Elements](https://github.com/stoplightio/elements).

Additionally, the root `/schema/` path is accessible, serving the site that is configured as the default in
the [OpenAPIConfig][starlite.config.OpenAPIConfig].

## Subclassing OpenAPIController

You can use your own subclass of [OpenAPIController][starlite.openapi.controller.OpenAPIController] by setting it as
then controller to use in the [OpenAPIConfig][starlite.config.OpenAPIConfig] `openapi_controller` kwarg.

For example, lets say we wanted to change the base path of the OpenAPI related endpoints from `/schema` to `/api-docs`, in this case we'd the following:

```python
from starlite import Starlite, OpenAPIController, OpenAPIConfig


class MyOpenAPIController(OpenAPIController):
    path = "/api-docs"


app = Starlite(
    route_handlers=[...],
    openapi_config=OpenAPIConfig(
        title="My API", version="1.0.0", openapi_controller=MyOpenAPIController
    ),
)
```

## Controller Class Attributes

The [OpenAPIController][starlite.openapi.controller.OpenAPIController] class defines the following class attributes that
can be customized by subclassing::

- `style`: base css for the page.
- `favicon_url`: url pointing at a `.ico` file to use as a favicon.
- `redoc_version`: version of redoc to use.
- `swagger_ui_version`: version of Swagger-UI to use.
- `stoplight_elements_version`: version of Stoplight Elements to use.
