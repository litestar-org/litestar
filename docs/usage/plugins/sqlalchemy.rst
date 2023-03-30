SQLAlchemy Plugins
==================

Starlite comes with built-in support for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ via
the :class:`SQLAlchemyInitPlugin <.contrib.sqlalchemy.init_plugin.plugin.SQLAlchemyInitPlugin>`.

Features
--------

* Managed `sessions <https://docs.sqlalchemy.org/en/14/orm/session.html>`_ (sync and async) including dependency injection
* Managed `engine <https://docs.sqlalchemy.org/en/14/core/engines.html>`_ (sync and async) including dependency injection
* Typed configuration objects

Basic Use
---------

You can simply pass an instance of :class:`SQLAlchemyInitPlugin <.contrib.sqlalchemy.init_plugin.plugin.SQLAlchemyInitPlugin>`
to the Starlite constructor. This will automatically create a SQLAlchemy engine and session for you, and make them
available to your handlers and dependencies via dependency injection.

.. tab-set::

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/sqlalchemy_async.py
            :caption: sqlalchemy_plugin.py
            :language: python


    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/sqlalchemy_sync.py
            :caption: sqlalchemy_plugin.py
            :language: python


Configuration
-------------

You configure the Plugin using either
:class:`SQLAlchemyAsyncConfig <.contrib.sqlalchemy.init_plugin.config.asyncio.SQLAlchemyAsyncConfig>` or
:class:`SQLAlchemySyncConfig <.contrib.sqlalchemy.init_plugin.config.sync.SQLAlchemySyncConfig>`.
