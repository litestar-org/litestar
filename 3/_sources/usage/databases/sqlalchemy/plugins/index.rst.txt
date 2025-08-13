Plugins
-------

Litestar has a plugin system that allows you to extend the functionality of the application. Plugins are passed to the
application at startup and can pre-configure the application to manage resources, add routes, and more.

A suite of plugins is available in :doc:`contrib.sqlalchemy.plugins </reference/contrib/sqlalchemy/plugins>` to support
using Litestar with SQLAlchemy, these include:

- :class:`litestar.contrib.sqlalchemy.plugins.SQLAlchemyPlugin`: Full SQLAlchemy support
- :class:`litestar.contrib.sqlalchemy.plugins.SQLAlchemyInitPlugin`: Application tooling
- :class:`litestar.contrib.sqlalchemy.plugins.SQLAlchemySerializationPlugin`: Serialization support

Each of the plugins is discussed in detail in the following sections.

.. toctree::
    sqlalchemy_plugin
    sqlalchemy_init_plugin
    sqlalchemy_serialization_plugin
