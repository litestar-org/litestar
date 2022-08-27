# OpenAPI Schema Generation Config

OpenAPI schema generation is enabled by default. To configure it you can pass an instance of
[OpenAPIConfig][starlite.config.OpenAPIConfig] to the Starlite constructor using the `openapi_config` kwarg:

```python
from starlite import Starlite, OpenAPIConfig

app = Starlite(
    route_handlers=[...], openapi_config=OpenAPIConfig(title="My API", version="1.0.0")
)
```

Aside from `title` and `version`, both of which are **required**, you can pass the following optional kwargs:

- `components`: An instance of [Components][pydantic_openapi_schema.v3_1_0.components.Components] or list of instances.
  If a list is provided, its members will be merged recursively into a single instance.
- `contact`: An instance of the [Contact][pydantic_openapi_schema.v3_1_0.contact.Contact].
- `create_examples`: Boolean flag dictating whether examples will be auto-generated using
  the [pydantic-factories](https://github.com/starlite-api/pydantic-factories) library. Defaults to `False`.
- `description`: Description text.
- `external_docs`: An instance of
  the [ExternalDocumentation][pydantic_openapi_schema.v3_1_0.external_documentation.ExternalDocumentation].
- `license`: An instance of the [License][pydantic_openapi_schema.v3_1_0.license.License].
- `openapi_controller`: The controller class to use for the openapi to generate the openapi related routes. Must be a
  subclass of [the openapi controller class](#the-openapi-controller).
- `security`: An instance of
  the [SecurityRequirement][pydantic_openapi_schema.v3_1_0.security_requirements.SecurityRequirements]
- `servers`: A list of [Server][pydantic_openapi_schema.v3_1_0.server.Server] instances. Defaults to `[Server("/")]`
- `summary`: Summary text.
- `tags`: A list of [Tag][pydantic_openapi_schema.v3_1_0.tag.Tag] instances.
- `terms_of_service`: A url to a page containing the terms of service.
- `use_handler_docstrings`: Boolean flag dictating whether to use route handler docstring to generate descriptions.
- `webhooks`: A string keyed dictionary of [PathItem][pydantic_openapi_schema.v3_1_0.path_item.PathItem] instances.

## Disabling Schema Generation

If you wish to disable schema generation and not include the schema endpoints in your API, simply pass `None` as the
value for `openapi_config`:

```python
from starlite import Starlite

app = Starlite(route_handlers=[...], openapi_config=None)
```

## Viewing the API Documentation in ReDoc

Starlite comes with integration of [ReDoc API Documentation Page](https://redoc.ly/) to render your OpenAPI schema as an
interactive web user interface. If your app is running locally on port 8000 you can access the
[ReDoc page at http://0.0.0.0:8000/schema](http://0.0.0.0:8000/schema). The ReDoc page will show and document all your
routes,
DTOs, and any metadata attached to your controllers mentioned above.

## Accessing the OpenAPI Schema

The generated schema is an instance of the `OpenAPI` pydantic model, and you can access it in any route handler like so:

```python
from starlite import Request, get


@get(path="/")
def my_route_handler(request: Request) -> dict:
    schema = request.app.openapi_schema
    return schema.dict()
```

##
