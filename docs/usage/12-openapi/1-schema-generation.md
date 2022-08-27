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
  subclass of [the openapi controller class](3-openapi-controller.md).
- `security`: An instance of the [SecurityRequirement][pydantic_openapi_schema.v3_1_0.security_requirement.SecurityRequirement]
- `servers`: A list of [Server][pydantic_openapi_schema.v3_1_0.server.Server] instances. Defaults to `[Server("/")]`
- `summary`: Summary text.
- `tags`: A list of [Tag][pydantic_openapi_schema.v3_1_0.tag.Tag] instances.
- `terms_of_service`: A url to a page containing the terms of service.
- `use_handler_docstrings`: Boolean flag dictating whether to use route handler docstring to generate descriptions.
- `webhooks`: A string keyed dictionary of [PathItem][pydantic_openapi_schema.v3_1_0.path_item.PathItem] instances. #
- `root_schema_site`: Dictates which schema site is served by default.
  The value should be one of `redoc`, `swagger`, `elements`, with the default be `redoc`.

## Disabling Schema Generation

If you wish to disable schema generation and not include the schema endpoints in your API, simply pass `None` as the
value for `openapi_config`:

```python
from starlite import Starlite

app = Starlite(route_handlers=[...], openapi_config=None)
```
