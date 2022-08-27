# OpenAPI Integration

Starlite has first class OpenAPI support offering the following features:

1. Automatic [OpenAPI 3.1.0 Schema](https://spec.openapis.org/oas/v3.1.0) generation, which is available as both YAML
   and JSON.
2. Builtin support for static documentation site generation using several different libraries.
3. Simple configuration using pydantic based classes.

## Pydantic-OpenAPI-Schema

Starlite generates the [latest version of the OpenAPI specification](https://spec.openapis.org/oas/latest.html) using
the [pydantic-openapi-schema](https://github.com/starlite-api/pydantic-openapi-schema) library, which is bundled as part
of Starlite and is also maintained by the [starlite-api](https://github.com/starlite-api) GitHub organization.

This library offers a full implementation of the OpenAPI specification as pydantic models, and is as such a powerful and
type correct foundation for schema generation using python.

!!! tip
    You can refer to the [pydantic-openapi-schema doc](https://starlite-api.github.io/pydantic-openapi-schema/) for a
    full reference regarding the library's API.
