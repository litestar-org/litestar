Plugins
=======

Litestar supports extension through plugins, which allow for the following:

1. Configuration support for working with 3rd party libraries
2. Serialization and OpenAPI support for types that aren't supported by default

InitPluginProtocol
~~~~~~~~~~~~~~~~~~

The :class:`litestar.plugins.InitPluginProtocol` protocol provides an object-based hook into the Litestar application
configuration process, on initialization of the application.

These plugins must have an ``on_app_init()`` method, that receives the :class:`litestar.config.app.AppConfig` object as
its only argument. This method can be used to modify the configuration object before it is used to configure the
application and is great for registering :doc:`Life Cycle Hooks </usage/lifecycle-hooks>`, configuring
:ref:`App State <Initializing Application State>`, and more.

SerializationPluginProtocol
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :class:`litestar.plugins.SerializationPluginProtocol` protocol provides a app layer hook to support
(de)sererialization and marshalling of types that aren't natively supported by Litestar.

Implementations of these plugins must have the following methods:

- ``supports_type()``
- ``create_dto_for_type()``


Creating Plugins
----------------

.. toctree::
    :titlesonly:
    :hidden:

    sqlalchemy/index
