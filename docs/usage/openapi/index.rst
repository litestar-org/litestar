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

Schema Availability
-------------------

By default, the generated OpenAPI schema is available at the following endpoints, relative to the configured ``openapi_path`` (which defaults to ``/schema``):

- ``/openapi.json``: The schema in JSON format.
- ``/openapi.yaml``: The schema in YAML format.
- ``/openapi.yml``: An alias for the YAML schema.

These endpoints are particularly useful for importing the schema into 3rd party tools, such as the Scalar API client or Postman.

.. toctree::

    schema_generation
    ui_plugins
