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

See the [API Reference][starlite.openapi.controller.OpenAPIController] for full details on the `OpenAPIController` class
and the kwargs it accepts.
