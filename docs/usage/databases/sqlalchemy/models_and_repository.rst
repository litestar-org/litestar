SQLAlchemy Models & Repository
==============================

Litestar comes with a built-in repository class
(:class:`SQLAlchemyAsyncRepository <advanced_alchemy.repository.SQLAlchemyAsyncRepository>`)
for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ to make CRUD operations easier.  These abstractions are stored in the companion `Advanced Alchemy <https://docs.advanced-alchemy.jolt.rs/latest/>`_.

What is Advanced Alchemy?
-------------------------
A carefully crafted, thoroughly tested, optimized companion library for
SQLAlchemy, offering features such as:

-  Sync and async repositories, featuring common CRUD and highly
   optimized bulk operations

-  Integration with major web frameworks including Litestar, Starlette,
   FastAPI, Sanic.

-  Custom-built alembic configuration and CLI with optional framework
   integration

-  Utility base classes with audit columns, primary keys and utility
   functions

-  Optimized JSON types including a custom JSON type for Oracle.

-  Integrated support for UUID6 and UUID7 using
   `uuid-utils` <https://github.com/aminalaee/uuid-utils>`__ (install
   with the ``uuid`` extra)

-  Pre-configured base classes with audit columns UUID or Big Integer
   primary keys and a `sentinel
   column <https://docs.sqlalchemy.org/en/20/core/connections.html#configuring-sentinel-columns>`__.

-  Synchronous and asynchronous repositories featuring:

   -  Common CRUD operations for SQLAlchemy models
   -  Bulk inserts, updates, upserts, and deletes with dialect-specific
      enhancements
   -  `lambda_stmt <https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.lambda_stmt>`__
      when possible for improved query building performance
   -  Integrated counts, pagination, sorting, filtering with ``LIKE``,
      ``IN``, and dates before and/or after.

-  Tested support for multiple database backends including:

   -  SQLite via
      `aiosqlite <https://aiosqlite.omnilib.dev/en/stable/>`__ or
      `sqlite <https://docs.python.org/3/library/sqlite3.html>`__
   -  Postgres via
      `asyncpg <https://magicstack.github.io/asyncpg/current/>`__ or
      `psycopg3 (async or sync) <https://www.psycopg.org/psycopg3/>`__
   -  MySQL via `asyncmy <https://github.com/long2ice/asyncmy>`__
   -  Oracle via `oracledb (async or
      sync) <https://oracle.github.io/python-oracledb/>`__ (tested on
      18c and 23c)
   -  Google Spanner via
      `spanner-sqlalchemy <https://github.com/googleapis/python-spanner-sqlalchemy/>`__
   -  DuckDB via
      `duckdb_engine <https://github.com/Mause/duckdb_engine>`__
   -  Microsoft SQL Server via
      `pyodbc <https://github.com/mkleehammer/pyodbc>`__ or
      `aioodbc <https://github.com/aio-libs/aioodbc>`__
   -  CockroachDB via `sqlalchemy-cockroachdb (async or
      sync) <https://github.com/cockroachdb/sqlalchemy-cockroachdb>`__

Basic Use
---------

To use the :class:`SQLAlchemyAsyncRepository <advanced_alchemy.repository.SQLAlchemyAsyncRepository>`
repository, you must first define your models using one of the included built-in ``DeclarativeBase`` ORM base
implementations:

* :class:`UUIDBase <advanced_alchemy.base.UUIDBase>`
* :class:`UUIDAuditBase <advanced_alchemy.base.UUIDAuditBase>`

Both include a ``UUID`` based primary key
and ``UUIDAuditBase`` includes an ``updated_at`` and ``created_at`` timestamp column.

The ``UUID`` will be a native ``UUID``/``GUID`` type on databases that support it such as Postgres.  For other engines without
a native UUID data type, the UUID is stored as a 16-byte ``BYTES`` or ``RAW`` field.

* :class:`BigIntBase <advanced_alchemy.base.BigIntBase>`
* :class:`BigIntAuditBase <advanced_alchemy.base.BigIntAuditBase>`

Both include a ``BigInteger`` based primary key
and ``BigIntAuditBase`` includes an ``updated_at`` and ``created_at`` timestamp column.

Models using these bases also include the following enhancements:

* Auto-generated snake-case table name from class name
* Pydantic BaseModel and Dict classes map to an optimized JSON type that is
  :class:`JSONB <sqlalchemy.dialects.postgresql.JSONB>` for Postgres,
  `VARCHAR` or `BYTES` with JSON check constraint for Oracle, and
  :class:`JSON <sqlalchemy.types.JSON>` for other dialects.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_declarative_models.py
    :caption: sqlalchemy_declarative_models.py
    :language: python

Basic Controller Integration
-----------------------------

Once you have declared your models, you are ready to use the ``SQLAlchemyAsyncRepository`` class with
your controllers and function based routes.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :caption: sqlalchemy_async_repository.py
    :language: python

Alternately, you may use the ``SQLAlchemySyncRepository`` class for your synchronous database connection.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_sync_repository.py
    :caption: sqlalchemy_sync_repository.py
    :language: python

.. seealso::

    * :doc:`/tutorials/repository-tutorial/index`
