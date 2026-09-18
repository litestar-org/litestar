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

Default OpenAPI schema files
----------------------------

When ``openapi_config`` is enabled, Litestar serves documentation UIs **and** the raw OpenAPI document
from the configured base path (default ``/schema``).

With the default configuration you can always fetch:

- ``/schema/openapi.json`` — the OpenAPI document as JSON

Some render plugins also expose YAML (or ``.yml``) variants when they register those paths, for example
``/schema/openapi.yaml``. Check the plugin documentation or ``openapi_config.render_plugins`` for the exact
paths in your app.

The UI root (for example ``/schema/`` when a default UI plugin is configured) is separate from the schema file
endpoints above. If you mount the app under an ASGI ``root_path`` and leave ``servers`` at the default ``/``,
Litestar will use that ``root_path`` as the OpenAPI server URL when the schema is served.

.. toctree::

    schema_generation
    ui_plugins

