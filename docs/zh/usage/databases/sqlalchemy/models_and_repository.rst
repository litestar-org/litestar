SQLAlchemy 模型与仓储
==============================

Litestar 内置了一个仓储类（:class:`SQLAlchemyAsyncRepository <advanced_alchemy.repository.SQLAlchemyAsyncRepository>`），用于 `SQLAlchemy <https://docs.sqlalchemy.org/>`_，使 CRUD 操作更加简单。

特性
--------

* 为 :doc:`SQLAlchemy <sqlalchemy:index>` 2.0 预配置的 ``DeclarativeBase``，包含基于 UUID 或 Big Integer 的主键、`哨兵列 <https://docs.sqlalchemy.org/en/20/core/connections.html#configuring-sentinel-columns>`_，以及可选的带审计列的版本。
* 用于 SQLAlchemy 模型的通用同步和异步仓储，支持选择、插入、更新和删除操作
* 实现了批量插入、更新和删除的优化方法，并在可能的情况下使用 `lambda_stmt <https://docs.sqlalchemy.org/en/20/core/sqlelement.html#sqlalchemy.sql.expression.lambda_stmt>`_。
* 集成的计数、分页、排序、使用 ``LIKE``、``IN`` 以及日期前后过滤。
* 经过测试支持多个数据库后端，包括：

  - SQLite 通过 `aiosqlite <https://aiosqlite.omnilib.dev/en/stable/>`_ 或 `sqlite <https://docs.python.org/3/library/sqlite3.html>`_
  - Postgres 通过 `asyncpg <https://magicstack.github.io/asyncpg/current/>`_ 或 `psycopg3（异步或同步） <https://www.psycopg.org/psycopg3/>`_
  - MySQL 通过 `asyncmy <https://github.com/long2ice/asyncmy>`_
  - Oracle 通过 `oracledb <https://oracle.github.io/python-oracledb/>`_
  - Google Spanner 通过 `spanner-sqlalchemy <https://github.com/googleapis/python-spanner-sqlalchemy/>`_
  - DuckDB 通过 `duckdb_engine <https://github.com/Mause/duckdb_engine>`_
  - Microsoft SQL Server 通过 `pyodbc <https://github.com/mkleehammer/pyodbc>`_

基本使用
---------

要使用 :class:`SQLAlchemyAsyncRepository <advanced_alchemy.repository.SQLAlchemyAsyncRepository>` 仓储，您必须首先使用包含的内置 ``DeclarativeBase`` ORM 基础实现之一定义模型：

* :class:`UUIDBase <advanced_alchemy.base.UUIDBase>`
* :class:`UUIDAuditBase <advanced_alchemy.base.UUIDAuditBase>`

两者都包含基于 ``UUID`` 的主键，``UUIDAuditBase`` 包含 ``updated_at`` 和 ``created_at`` 时间戳列。

``UUID`` 将是支持它的数据库（如 Postgres）上的原生 ``UUID``/``GUID`` 类型。对于其他没有原生 UUID 数据类型的引擎，UUID 存储为 16 字节的 ``BYTES`` 或 ``RAW`` 字段。

* :class:`BigIntBase <advanced_alchemy.base.BigIntBase>`
* :class:`BigIntAuditBase <advanced_alchemy.base.BigIntAuditBase>`

两者都包含基于 ``BigInteger`` 的主键，``BigIntAuditBase`` 包含 ``updated_at`` 和 ``created_at`` 时间戳列。

使用这些基类的模型还包括以下增强功能：

* 从类名自动生成蛇形命名法的表名
* Pydantic BaseModel 和 Dict 类映射到优化的 JSON 类型，对于 Postgres 是 :class:`JSONB <sqlalchemy.dialects.postgresql.JSONB>`，对于 Oracle 是带 JSON 检查约束的 `VARCHAR` 或 `BYTES`，对于其他方言是 :class:`JSON <sqlalchemy.types.JSON>`。

.. literalinclude:: /examples/sqla/sqlalchemy_declarative_models.py
    :caption: ``sqlalchemy_declarative_models.py``
    :language: python

基本控制器集成
-----------------------------

声明模型后，您就可以在控制器和基于函数的路由中使用 ``SQLAlchemyAsyncRepository`` 类了。

.. literalinclude:: /examples/sqla/sqlalchemy_async_repository.py
    :caption: ``sqlalchemy_async_repository.py``
    :language: python

或者，您可以为同步数据库连接使用 ``SQLAlchemySyncRepository`` 类。

.. literalinclude:: /examples/sqla/sqlalchemy_sync_repository.py
    :caption: ``sqlalchemy_sync_repository.py``
    :language: python

.. seealso::

    * :doc:`/tutorials/repository-tutorial/index`
