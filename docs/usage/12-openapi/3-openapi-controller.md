# The OpenAPIController

Starlite includes an [`OpenAPIController`][starlite.openapi.controller.OpenAPIController] class that is used as the
default controller in the [OpenAPIConfig](1-schema-generation.md).

This controller exposes the following endpoints:

- `/schema/openapi.yaml`: allowing for download of the OpenAPI schema as YAML.
- `/schema/openapi.json`: allowing for download of the OpenAPI schema as JSON.
- `/schema/redoc`: which serve the docs using [Redoc](https://github.com/Redocly/redoc).
- `/schema/swagger`: which serves the docs using [Swagger-UI](https://swagger.io/docs/open-source-tools/swagger-ui/).
- `/schema/elements`: which serves the docs using [Stoplight Elements](https://github.com/stoplightio/elements).

Additionally, the root `/schema/` path is accessible, serving the site that is configured as the default in
the [`OpenAPIConfig`][starlite.config.OpenAPIConfig].

## Subclassing OpenAPIController

You can use your own subclass of [`OpenAPIController`][starlite.openapi.controller.OpenAPIController] by setting it as
then controller to use in the [`OpenAPIConfig`][starlite.config.OpenAPIConfig] `openapi_controller` kwarg.

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

## CDN and offline file support

You can change the default download paths for JS and CSS bundles as well as google fonts by subclassing [`OpenAPIController`][starlite.openapi.controller.OpenAPIController]  and setting any of the following class variables:

```python
from starlite import Starlite, OpenAPIController, OpenAPIConfig


class MyOpenAPIController(OpenAPIController):
    path = "/api-docs"
    redoc_google_fonts = False
    redoc_js_url = "https://offline_location/redoc.standalone.js"
    swagger_css_url = "https://offline_location/swagger-ui-css"
    swagger_ui_bundle_js_url = "https://offline_location/swagger-ui-bundle.js"
    swagger_ui_standalone_preset_js_url = (
        "https://offline_location/swagger-ui-standalone-preset.js"
    )
    stoplight_elements_css_url = "https://offline_location/spotlight-styles.mins.css"
    stoplight_elements_js_url = (
        "https://offline_location/spotlight-web-components.min.js"
    )


app = Starlite(
    route_handlers=[...],
    openapi_config=OpenAPIConfig(
        title="My API", version="1.0.0", openapi_controller=MyOpenAPIController
    ),
)
```
