# The OpenAPI Controller

Starlite includes an [OpenAPIController][starlite.openapi.controller.OpenAPIController] class that is used as the default controller in the [OpenAPIConfig](1-schema-generation.md).

This controller exposes the following endpoints:

- `/schema/openapi.yaml`: allowing for download of the OpenAPI schema as YAML.
- `/schema/openapi.json`: allowing for download of the OpenAPI schema as JSON.
- `/schema/redoc`: which serve the docs using [Redoc](https://github.com/Redocly/redoc).
- `/schema/swagger`: which serves the docs using[Swagger-UI](https://swagger.io/docs/open-source-tools/swagger-ui/).
- `/schema/elements`: which serves the docs using [Stoplight Elements](https://github.com/stoplightio/elements).

Additionally, the root `/schema/` path is accessible, seving the `redoc` site by default.

If you would like to modify the base path, add new endpoints, change the styling of the page etc., you can subclass the
`OpenAPIController` and then pass your subclass to the `OpenAPIConfig`.

For example, lets say we wanted to change the base path from "/schema" to "/api-docs":

```python
from starlite import OpenAPIController


class MyOpenAPIController(OpenAPIController):
    path = "/api-docs"
```

The following extra attributes are defined on this controller and are customizable:

- `style`: base css for the page.
- `favicon_url`: url pointing at `.ico` file to use as a favicon.
- `redoc_version`: version of redoc to use.
- `swagger_ui_version`: version of Swagger-UI to use.
- `stoplight_elements_version`: version of Stoplight Elements to use.

We would then use the subclassed controller like so:

```python
from starlite import Starlite, OpenAPIConfig, OpenAPIController


class MyOpenAPIController(OpenAPIController):
    path = "/api-docs"


app = Starlite(
    route_handlers=[...],
    openapi_config=OpenAPIConfig(openapi_controller=MyOpenAPIController),
)
```

The root handler serves Redoc by default via `render_redoc`. You can override the `root` handler to serve other included
documentation, such as Swagger UI by returning `render_swagger_ui` or Stoplight Elements
with `render_stoplight_elements`. You can also have it serve your own [template](../15-templating.md):

```python
from starlite import OpenAPIController, Request, get
from starlite.enums import MediaType


class MyOpenAPIController(OpenAPIController):
    path = "/"

    @get(path="/", media_type=MediaType.HTML, include_in_schema=False)
    def root(self, request: Request) -> str:
        return self.render_swagger_ui(request)
```
