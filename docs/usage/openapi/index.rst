OpenAPI
=======

Litestar has first class OpenAPI support offering the following features:

- Automatic `OpenAPI 3.1.0 Schema <https://spec.openapis.org/oas/v3.1.0>`_ generation, which is available as both YAML
  and JSON.
- Builtin support for static documentation site generation using several different libraries.
- Full configuration using pre-defined type-safe dataclasses.


Litestar includes a complete implementation of the `latest version of the OpenAPI specification <https://spec.openapis.org/oas/latest.html>`_
using Python dataclasses. This implementation is used as a basis for generating OpenAPI specs,
supporting :func:`~dataclasses.dataclass`, :class:`~typing.TypedDict`,
as well as Pydantic and msgspec models, and any 3rd party entities
for which a :ref:`plugin <plugins>` is implemented.

This is also highly configurable - and users can customize the OpenAPI spec in a variety of ways - ranging from passing
configuration globally to setting
:ref:`specific kwargs on route <usage/openapi/schema_generation:Configuring schema generation on a route handler>`
handler decorators.

Default schema endpoints
------------------------

By default, the OpenAPI schema is served at ``/schema`` (configurable via
:attr:`OpenAPIConfig.path <litestar.openapi.config.OpenAPIConfig.path>`).
The following endpoints are available under the configured path:

- ``/schema/openapi.json`` — OpenAPI schema as JSON
- ``/schema/openapi.yaml`` — OpenAPI schema as YAML

These endpoints can be used to import the schema into API clients such as
`Scalar API Client <https://scalar.com/>`_ or other OpenAPI-compatible tools.

.. toctree::

    schema_generation
    ui_plugins
