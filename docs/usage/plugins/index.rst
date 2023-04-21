Plugins
=======

Litestar supports extension through plugins, which allow for the following:

1. Configuration support for working with 3rd party libraries
2. Serialization and OpenAPI support for types that aren't supported by default

InitPluginProtocol
~~~~~~~~~~~~~~~~~~

The :class:`litestar.plugins.InitPluginProtocol` protocol provides an object-based hook into Litestar application
configuration.

These plugins must have an ``on_app_init()`` method, that receives the :class:`litestar.config.app.AppConfig` object as
its only argument. This method can be used to modify the configuration object before it is used to configure the
application and is great for registering :doc:`Life Cycle Hooks </usage/lifecycle-hooks>`, configuring
:ref:`App State <Initializing Application State>`, and more.

Creating an InitPluginProtocol implementation
---------------------------------------------

TODO

SerializationPluginProtocol
~~~~~~~~~~~~~~~~~~~~~~~~~~~

The :class:`litestar.plugins.SerializationPluginProtocol` protocol provides a app layer hook to support
(de)sererialization and marshalling of types that aren't natively supported by Litestar.

Implementations of these plugins must have the following methods:

- ``supports_type()``
- ``create_dto_for_type()``

These work by providing a :class:`litestar.dto.interface.DTOInterface` type for any `"data"` kwarg type, or handler
return type, that doesn't otherwise have a ``DTOInterface`` type configured, and that is supported by the plugin.

Creating a SerializationPluginProtocol implementation
-----------------------------------------------------

TODO

.. toctree::
    :titlesonly:
    :hidden:

    sqlalchemy/index
