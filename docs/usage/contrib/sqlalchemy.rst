SQLAlchemy Repository
=====================

Litestar comes with a built-in repository class (:class:`SQLAlchemyRepository <.contrib.sqlalchemy.repository.SQLAlchemyRepository>`.) for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ to make CRUD operations easier.

Features
--------

* Pre-configured `DeclarativeBase` for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ 2.0 that includes a UUID based primary-key and an optional version with audit columns.
* Generic repository select, insert, update, and delete operations for SQLAlchemy models
* Implements optimized methods for bulk inserts, updates, and deletes.  
* Support for SQLite via `aiosqlite`, Postgres via `asyncpg` and MySQL via `asyncmy`

Basic Use
---------

You can simply pass an instance of :class:`SQLAlchemyInitPlugin <.contrib.sqlalchemy.init_plugin.plugin.SQLAlchemyInitPlugin>`
to the Litestar constructor. This will automatically create a SQLAlchemy engine and session for you, and make them
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

TODO



Dependency Injection
--------------------

TODO



Extending
---------

TODO

