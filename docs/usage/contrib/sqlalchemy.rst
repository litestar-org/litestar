SQLAlchemy Models & Repository
==============================

Litestar comes with a built-in repository class (:class:`AsyncSQLAlchemyRepository <litestar.contrib.sqlalchemy.repository.AsyncSQLAlchemyRepository>`.) for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ to make CRUD operations easier.

Features
--------

* Pre-configured `DeclarativeBase` for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ 2.0 that includes a UUID based primary-key and an optional version with audit columns.
* Generic asynchronous repository for select, insert, update, and delete operations on SQLAlchemy models
* Implements optimized methods for bulk inserts, updates, and deletes.
* Integrated counts, pagination, filtering with `LIKE`, `IN`, and dates before and/or after.
* Support for SQLite via `aiosqlite` and Postgres via `asyncpg`

Basic Use
---------

To use the `AsyncSQLAlchemyRepository` repository, you must first define your models using one of the included built-in `DeclarativeBase` ORM base implementations  (`Base` and `AuditBase`).  Both include a UUID based primary key and `AuditBase` includes an `updated` and `created` timestamp column.

Models using these bases also include the following enhancements:
* Auto-generated snake-case table name from class name
* Pydantic BaseModel and Dict classes map to JSONB SQLAlchemy type map

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_declarative_models.py
    :caption: sqlalchemy_declarative_models.py
    :language: python

Basic Controller Integration.
-----------------------------

Once you have declared your models, you are ready to use the :class:`AsyncSQLAlchemyRepository <litestar.contrib.sqlalchemy.repository.AsyncSQLAlchemyRepository>` class with your controllers and function based routes.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :caption: sqlalchemy_async_repository.py
    :language: python
