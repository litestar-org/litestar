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

Default schemas
---------------

Litestar serves the generated OpenAPI schema at paths under :attr:`OpenAPIConfig.path`, which defaults to ``/schema``.
With the default configuration, the JSON schema is available at ``GET /schema/openapi.json``.

Litestar always registers a handler for ``/openapi.json`` under the schema root path, even when
``JsonRenderPlugin`` is not included in :attr:`OpenAPIConfig.render_plugins`.

YAML schema files are not served by default. To expose ``/openapi.yaml`` and ``/openapi.yml``, add
:class:`YamlRenderPlugin` to :attr:`OpenAPIConfig.render_plugins`. Rendering YAML requires
the `PyYAML <https://pyyaml.org/wiki/PyYAMLDocumentation>`_ library, which can be installed via the ``litestar[yaml]``
package extra. See the YAML tab in :doc:`OpenAPI UI Plugins </usage/openapi/ui_plugins>` for an example.

To change the schema root path, set :attr:`OpenAPIConfig.path`. For example, configuring the path as ``/docs`` serves
the JSON schema at ``/docs/openapi.json``. See :doc:`Configuring the OpenAPI Root Path </usage/openapi/ui_plugins>` for
details.

When providing a custom :attr:`OpenAPIConfig.openapi_router`, ``path`` is ignored and routes are registered on that
router instead.

Do not register application route handlers that conflict with paths used by OpenAPI render plugins. Conflicting routes
can prevent the schema or documentation UI from being served correctly. Requests to unknown schema paths ending in
``.json``, ``.yaml``, or ``.yml`` return a ``404 Not Found`` response.

The schema is also available programmatically via :attr:`~litestar.app.Litestar.openapi_schema`.


.. toctree::

    schema_generation
    ui_plugins
