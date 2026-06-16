OpenAPI
=======

Litestar has first class OpenAPI support offering the following features:

- Automatic `OpenAPI 3.1.0 Schema <https://spec.openapis.org/oas/v3.1.0>`_ generation, which is available as both YAML
  and JSON.
- Builtin support for static documentation site generation using several different libraries.
- Full configuration using pre-defined type-safe dataclasses.

Default OpenAPI Files
---------------------

Litestar automatically serves the generated OpenAPI schema as downloadable files at the
following endpoints, relative to the configured schema path (``/schema`` by default):

- ``/schema/openapi.json`` -- The full OpenAPI schema in JSON format.
- ``/schema/openapi.yaml`` -- The full OpenAPI schema in YAML format.
- ``/schema/openapi.yml`` -- Alias for the YAML format.

These files are useful for importing the API definition into external tools such as
`Scalar API client <https://github.com/scalar/scalar>`_, Postman, or any other
OpenAPI-compatible tool. For example, with the default configuration::

    https://your-app.example.com/schema/openapi.json

If you have customized the OpenAPI path (see :ref:`OpenAPI Root Path <usage/openapi/ui_plugins:Configuring the OpenAPI Root Path>`),
replace ``/schema`` with your configured path. For instance, if the path is set to
``/docs``, the files would be available at ``/docs/openapi.json``,
``/docs/openapi.yaml``, and ``/docs/openapi.yml``.

Litestar includes a complete implementation
using Python dataclasses. This implementation is used as a basis for generating OpenAPI specs,
supporting :func:`~dataclasses.dataclass`, :class:`~typing.TypedDict`,
as well as Pydantic and msgspec models, and any 3rd party entities
for which a :ref:`plugin <plugins>` is implemented.

This is also highly configurable - and users can customize the OpenAPI spec in a variety of ways - ranging from passing
configuration globally to setting
:ref:`specific kwargs on route <usage/openapi/schema_generation:Configuring schema generation on a route handler>`
handler decorators.

.. toctree::

    schema_generation
    ui_plugins
