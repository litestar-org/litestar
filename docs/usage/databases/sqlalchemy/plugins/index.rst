Plugins
-------

Litestar has a plugin system that allows you to extend the functionality of the application. Plugins are passed to the
application at startup and can pre-configure the application to manage resources, add routes, and more.

A suite of plugins is available in :doc:`plugins.sqlalchemy </reference/contrib/sqlalchemy/plugins>` to support
using Litestar with SQLAlchemy, these include:

- :class:`litestar.plugins.sqlalchemy.SQLAlchemyPlugin`: Full SQLAlchemy support
- :class:`litestar.plugins.sqlalchemy.SQLAlchemyInitPlugin`: Application tooling
- :class:`litestar.plugins.sqlalchemy.SQLAlchemySerializationPlugin`: Serialization support

Each of the plugins is discussed in detail in the following sections.

.. toctree::
    sqlalchemy_plugin
    sqlalchemy_init_plugin
    sqlalchemy_serialization_plugin
