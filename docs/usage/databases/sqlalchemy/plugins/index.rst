Plugins
-------

Litestar has a plugin system that allows you to extend the functionality of the application. Plugins are passed to the
application at startup and can pre-configure the application to manage resources, add routes, and more.

A suite of plugins is available in :doc:`litestar.plugins.sqlalchemy </reference/plugins/sqlalchemy>` to support
using Litestar with SQLAlchemy, these include:

- :class:`advanced_alchemy.extensions.litestar.SQLAlchemyPlugin`: Full SQLAlchemy support
- :class:`advanced_alchemy.extensions.litestar.SQLAlchemyInitPlugin`: Application tooling
- :class:`advanced_alchemy.extensions.litestar.SQLAlchemySerializationPlugin`: Serialization support

Each of the plugins is discussed in detail in the following sections.

.. toctree::
    sqlalchemy_plugin
    sqlalchemy_init_plugin
    sqlalchemy_serialization_plugin
