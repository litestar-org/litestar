OpenAPI UI Plugins
------------------

OpenAPI UI Plugins are designed to allow easy integration with your OpenAPI UI framework of choice. These plugins
facilitate the creation of interactive, user-friendly API documentation, making it easier for developers and end-users
to understand and interact with the API.

In addition to serving a default JSON representation of the OpenAPI specification, built-in UI Plugins are available to
support a range of popular OpenAPI documentation tools, including:

- `RapiDoc <https://rapidocweb.com/>`_
- `ReDoc <https://redocly.com/>`_
- `Stoplight Elements <https://stoplight.io/open-source/elements>`_
- `Swagger UI <https://swagger.io/tools/swagger-ui/yy>`_
- `YAML <https://yaml.org/>`_ (OK, not a UI framework, but configured the same way!)

Each plugin is easily configurable, allowing developers to customize aspects like version, paths, CSS and JavaScript
resources.


Using OpenAPI UI Plugins
------------------------

Using OpenAPI UI Plugins is as simple as importing the plugin, instantiating it, and adding it to the OpenAPIConfig.

.. tab-set::

    .. tab-item:: rapidoc

        .. literalinclude:: /examples/openapi/plugins/rapidoc_simple.py
            :language: python

    .. tab-item:: redoc

        .. literalinclude:: /examples/openapi/plugins/redoc_simple.py
            :language: python

    .. tab-item:: stoplight

        .. literalinclude:: /examples/openapi/plugins/stoplight_simple.py
            :language: python

    .. tab-item:: swagger

        .. literalinclude:: /examples/openapi/plugins/swagger_ui_simple.py
            :language: python

    .. tab-item:: yaml

        .. literalinclude:: /examples/openapi/plugins/yaml_simple.py
            :language: python

    .. tab-item:: multiple

        .. literalinclude:: /examples/openapi/plugins/serving_multiple_uis.py
            :caption: Any combination of UIs can be served.
            :language: python
