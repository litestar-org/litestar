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


Accessing OpenAPI Schema Files
------------------------------

By default, the OpenAPI schema is available as a JSON file at ``{openapi_path}/openapi.json``. The default
``openapi_path`` is ``/schema``, so the JSON schema is served at ``/schema/openapi.json``.

This endpoint is useful when you need to import your API schema into external tools, such as
`Scalar <https://scalar.com/>`_ API client's collection import feature, `Postman <https://www.postman.com/>`_,
or other OpenAPI-compatible tools.

To also serve the schema as YAML, add the :class:`YamlRenderPlugin <litestar.openapi.plugins.YamlRenderPlugin>` to
your configuration:

.. code-block:: python

   from litestar import Litestar
   from litestar.openapi.config import OpenAPIConfig
   from litestar.openapi.plugins import ScalarRenderPlugin, YamlRenderPlugin

   app = Litestar(
       route_handlers=[...],
       openapi_config=OpenAPIConfig(
           title="My API",
           version="1.0.0",
           render_plugins=[ScalarRenderPlugin(), YamlRenderPlugin()],
       ),
   )

This makes the schema available at both ``/schema/openapi.yaml`` and ``/schema/openapi.yml``.

You can customize the root path by setting the :attr:`OpenAPIConfig.path <litestar.openapi.OpenAPIConfig.path>` attribute.
See :doc:`ui_plugins` for more details on configuring the OpenAPI root path.


.. toctree::

    schema_generation
    ui_plugins
