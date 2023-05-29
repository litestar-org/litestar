SQLAlchemy Init Plugin
----------------------

The :class:`SQLAlchemyInitPlugin <litestar.contrib.sqlalchemy.plugins.SQLAlchemyInitPlugin>` adds functionality to the
application that supports using Litestar with `SQLAlchemy <http://www.sqlalchemy.org/>`_.

The plugin:

- Makes the SQLAlchemy engine and session available via dependency injection.
- Manages the SQLAlchemy engine and session factory in the application's state.
- Configures a ``before_send`` handler that is called before sending a response.
- Includes relevant names in the signature namespace to aid resolving annotated types.

Dependencies
============

The plugin makes the engine and session available for injection.

.. tab-set::

   .. tab-item:: Async

        .. literalinclude:: /examples/contrib/sqlalchemy/plugins/sqlalchemy_async_dependencies.py
            :caption: SQLAlchemy Async Dependencies
            :language: python
            :linenos:

   .. tab-item:: Sync

        .. literalinclude:: /examples/contrib/sqlalchemy/plugins/sqlalchemy_sync_dependencies.py
            :caption: SQLAlchemy Sync Dependencies
            :language: python
            :linenos:

The above example illustrates how to access the engine and session in the handler, and like all other dependencies, they
can also be injected into other dependency functions.

Renaming the dependencies
#########################

You can change the name that the engine and session are bound to by setting the
:attr:`engine_dependency_key <litestar.contrib.sqlalchemy.plugins.GenericSQLAlchemyConfig.engine_dependency_key>` and
:attr:`session_dependency_key <litestar.contrib.sqlalchemy.plugins.GenericSQLAlchemyConfig.session_dependency_key>`
attributes on the plugin configuration.

Configuring the before send handler
###################################

The plugin configures a ``before_send`` handler that is called before sending a response. The default handler closes the
session and removes it from the connection scope.

You can change the handler by setting the
:attr:`before_send_handler <litestar.contrib.sqlalchemy.plugins.GenericSQLAlchemyConfig.before_send_handler>` attribute
on the configuration object. For example, an alternate handler is available that will also commit the session on success
and rollback upon failure.

.. tab-set::

   .. tab-item:: Async

        .. literalinclude:: /examples/contrib/sqlalchemy/plugins/sqlalchemy_async_before_send_handler.py
            :caption: SQLAlchemy Async Before Send Handler
            :language: python
            :linenos:

   .. tab-item:: Sync

        .. literalinclude:: /examples/contrib/sqlalchemy/plugins/sqlalchemy_sync_before_send_handler.py
            :caption: SQLAlchemy Sync Before Send Handler
            :language: python
            :linenos:

Example
=======

The below example is a complete demonstration of use of the init plugin. Readers who are familiar with the prior section
may note the additional complexity involved in managing the conversion to and from SQLAlchemy objects within the
handlers. Read on to see how this increased complexity is efficiently handled by the
:class:`SQLAlchemySerializationPlugin <litestar.contrib.sqlalchemy.plugins.SQLAlchemySerializationPlugin>`.

.. tab-set::

   .. tab-item:: Async

        .. literalinclude:: /examples/contrib/sqlalchemy/plugins/sqlalchemy_async_init_plugin_example.py
            :caption: SQLAlchemy Async Init Plugin Example
            :language: python
            :linenos:

   .. tab-item:: Sync

        .. literalinclude:: /examples/contrib/sqlalchemy/plugins/sqlalchemy_sync_init_plugin_example.py
            :caption: SQLAlchemy Sync Init Plugin Example
            :language: python
            :linenos:
