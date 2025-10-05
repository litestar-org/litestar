SQLAlchemy Init Plugin
----------------------

The :class:`SQLAlchemyInitPlugin <advanced_alchemy.extensions.litestar.SQLAlchemyInitPlugin>` adds functionality to the
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

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_dependencies.py
            :caption: SQLAlchemy Async Dependencies
            :language: python
            :linenos:

   .. tab-item:: Sync

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_dependencies.py
            :caption: SQLAlchemy Sync Dependencies
            :language: python
            :linenos:

The above example illustrates how to access the engine and session in the handler, and like all other dependencies, they
can also be injected into other dependency functions.

Renaming the dependencies
#########################

You can change the name that the engine and session are bound to by setting the
:attr:`engine_dependency_key <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig.engine_dependency_key>`
and :attr:`session_dependency_key <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig.session_dependency_key>`
attributes on the plugin configuration.

Configuring the before send handler
###################################

The plugin configures a ``before_send`` handler that is called before sending a response. The default handler closes the
session and removes it from the connection scope.

You can change the handler by setting the
:attr:`before_send_handler <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig.before_send_handler>`
attribute on the configuration object. For example, an alternate handler is available that will also commit the session
on success and rollback upon failure.

.. tab-set::

   .. tab-item:: Async

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_before_send_handler.py
            :caption: SQLAlchemy Async Before Send Handler
            :language: python
            :linenos:

   .. tab-item:: Sync

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_before_send_handler.py
            :caption: SQLAlchemy Sync Before Send Handler
            :language: python
            :linenos:

Configuring the plugins
#######################

Both the :class:`SQLAlchemyAsyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig>` and the
:class:`SQLAlchemySyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemySyncConfig>` have an ``engine_config``
attribute that is used to configure the engine. The ``engine_config`` attribute is an instance of
:class:`EngineConfig <advanced_alchemy.extensions.litestar.EngineConfig>` and exposes all of the configuration options
available to the SQLAlchemy engine.

The :class:`SQLAlchemyAsyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig>` class and the
:class:`SQLAlchemySyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemySyncConfig>` class also have a
``session_config`` attribute that is used to configure the session. This is either an instance of
:class:`AsyncSessionConfig <advanced_alchemy.extensions.litestar.AsyncSessionConfig>` or
:class:`SyncSessionConfig <advanced_alchemy.extensions.litestar.SyncSessionConfig>` depending on the type of config
object. These classes expose all of the configuration options available to the SQLAlchemy session.

Finally, the :class:`SQLAlchemyAsyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemyAsyncConfig>` class and the
:class:`SQLAlchemySyncConfig <advanced_alchemy.extensions.litestar.SQLAlchemySyncConfig>` class expose configuration
options to control their behavior.

Consult the reference documentation for more information.

Example
=======

The below example is a complete demonstration of use of the init plugin. Readers who are familiar with the prior section
may note the additional complexity involved in managing the conversion to and from SQLAlchemy objects within the
handlers. Read on to see how this increased complexity is efficiently handled by the
:class:`SQLAlchemySerializationPlugin <advanced_alchemy.extensions.litestar.SQLAlchemySerializationPlugin>`.

.. tab-set::

   .. tab-item:: Async

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_async_init_plugin_example.py
            :caption: SQLAlchemy Async Init Plugin Example
            :language: python
            :linenos:

   .. tab-item:: Sync

        .. literalinclude:: /examples/sqla/plugins/sqlalchemy_sync_init_plugin_example.py
            :caption: SQLAlchemy Sync Init Plugin Example
            :language: python
            :linenos:
