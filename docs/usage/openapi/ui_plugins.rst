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

Configuring OpenAPI UI Plugins
------------------------------

Each plugin can be tailored to meet your unique requirements by passing options at instantiation. For full details on
each plugins options, see the :doc:`API Reference </reference/openapi/plugins>`.

All plugins support the following options:

- ``path``: Each plugin has its own default, e.g., ``/rapidoc`` for RapiDoc. This can be overridden to serve the UI at
  a different path.
- ``media_type``: The default media type for the plugin, typically ``text/html``.
- ``favicon``: A string that should be a valid ``<link>`` tag, e.g.,
  ``<link rel="icon" href="https://example.com/favicon.ico">``.
- ``style``: Default is ``body { margin: 0; padding: 0; }``. This is applied to the ``<style>`` tag in the HTML rendered
  by the plugin.

Most plugins support the following additional options:

- ``version``: The version of the UIs JS and (in some cases) CSS bundle to use. We use the ``version`` to construct the
  URL to retrieve the the bundle from ``unpkg``, e.g., ``https://unpkg.com/rapidoc@<version>/dist/rapidoc-min.js``
- ``js_url``: The URL to the JS bundle. If provided, this will override the ``version`` option.
- ``css_url``: The URL to the CSS bundle. If provided, this will override the ``version`` option.

Here's some examples of configuring the plugins:

.. tab-set::

    .. tab-item:: rapidoc

        .. literalinclude:: /examples/openapi/plugins/rapidoc_config.py
            :language: python

    .. tab-item:: redoc

        .. literalinclude:: /examples/openapi/plugins/redoc_config.py
            :language: python

    .. tab-item:: stoplight

        .. literalinclude:: /examples/openapi/plugins/stoplight_config.py
            :language: python

    .. tab-item:: swagger

        .. literalinclude:: /examples/openapi/plugins/swagger_ui_config.py
            :language: python

Configuring the OpenAPI Root Path
---------------------------------

The OpenAPI root path is the path at which the OpenAPI representations are served. By default, this is ``/schema``.
This can be changed by setting the :attr:`OpenAPIConfig.path` attribute.

In the following example, we configure the OpenAPI root path to be ``/docs``:

.. literalinclude:: /examples/openapi/customize_path.py
    :language: python

This will result in any of the OpenAPI endpoints being served at ``/docs`` instead of ``/schema``, e.g.,
``/docs/openapi.json``.

Backward Compatibility
----------------------

OpenAPI UI plugins are a new feature introduced in ``v2.5.0``.

Providing a subclass of OpenAPIController
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The previous method of configuring elements such as the root path and styling was to subclass
:class:`OpenAPIController`, and set it on the :attr:`OpenAPIConfig.openapi_controller` attribute. This approach is now
deprecated and slated for removal in ``v3.0.0``, but if you are using it, there should be no change in behavior.

To maintain backward compatibility with the previous approach, if neither the :attr:`OpenAPIConfig.openapi_controller`
or :attr:`OpenAPIConfig.render_plugins` attributes are set, we will automatically add the plugins to respect the also
deprecated :attr:`OpenAPIConfig.enabled_endpoints` attribute. By default, this will result in the following endpoints
being enabled:

- ``/schema/openapi.json``
- ``/schema/redoc``
- ``/schema/rapidoc``
- ``/schema/elements``
- ``/schema/swagger``
- ``/schema/openapi.yml``
- ``/schema/openapi.yaml``

In ``v3.0.0``, the :attr:`OpenAPIConfig.enabled_endpoints` attribute will be removed, and only a single UI plugin will be
enabled by default, in addition to the ``openapi.json`` endpoint which will always be enabled.

Backward compatibility with root_schema_site
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Litestar has always supported a ``root_schema_site`` attribute on the :class:`OpenAPIConfig` class. This attribute
allowed you to elect to serve a UI at the OpenAPI root path, e.g., by default ``redoc`` would be served at both
``/schema`` and ``/schema/redoc``.

In ``v3.0.0``, the ``root_schema_site`` attribute will be removed, and the first :class:`OpenAPIRenderPlugin` in the
:attr:`OpenAPIConfig.render_plugins` list will be assigned to the ``/schema`` endpoint.

As of ``v2.5.0``, if you explicitly use the new :attr:`OpenAPIConfig.render_plugins` attribute, you will be
automatically opted in to the new behavior, and the ``root_schema_site`` attribute will be ignored.

Building your own OpenAPI UI Plugin
-----------------------------------

If Litestar does not have built-in support for your OpenAPI UI framework of choice, you can easily create your own
plugin by subclassing :class:`OpenAPIRenderPlugin` and implementing the :meth:`OpenAPIRenderPlugin.render` method.

To demonstrate building a custom plugin, we'll look at the :class:`RapidocRenderPlugin` class, that is maintained by
Litestar. Here's the finished product:

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python

Class definition
~~~~~~~~~~~~~~~~

The class ``RapidocRenderPlugin`` inherits from :class:`OpenAPIRenderPlugin`:

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 10

``__init__`` Constructor
~~~~~~~~~~~~~~~~~~~~~~~~

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 13-20

We support configuration via the following arguments:

- ``version``: Specifies the version of RapiDoc to use.
- ``js_url``: Custom URL to the RapiDoc JavaScript bundle.
- ``path``: The URL path where the RapiDoc UI will be served.
- ``**kwargs``: Captures additional arguments to pass to the superclass.

And we construct a url for the RapiDoc JavaScript bundle if it is not provided:

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 30

render()
~~~~~~~~

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 33

Finally we define the ``render`` method, which is called by Litestar to render the UI. It receives the a
:class:`Request` object and the ``openapi_schema`` as a dictionary.

Inside the ``render`` method, we construct the HTML to render the UI, and return it as a string.

- ``head``: Defines the HTML ``<head>`` section, including the title from ``openapi_schema``, a link to the RapiDoc
  script (``self.js_url``), and any additional styles (``self.style``).
- ``body``: Constructs the HTML ``<body>``, with a ``<rapi-doc>`` element pointing to the OpenAPI JSON specification
  endpoint.
- Returns a complete HTML document (as a byte string), combining head and body.

.. literalinclude:: /examples/openapi/plugins/custom_plugin.py
    :language: python
    :lines: 47-70

Interacting with the ``Router``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Internally, an instance of :class:`Router` is constructed to serve the OpenAPI endpoints. The ``Router`` is available
to plugins via the :meth:`OpenAPIRenderPlugin.receive_router` method.

This can be used for a variety of purposes, including adding additional routes to the ``Router``.

.. literalinclude:: /examples/openapi/plugins/receive_router.py
    :language: python
