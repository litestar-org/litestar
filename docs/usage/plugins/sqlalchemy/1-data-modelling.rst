Data Modelling
--------------

Our application is a simple one, it maintains a TODO list for our users and uses the ``TodoItem`` type to represent
these items.

.. literalinclude:: /examples/plugins/sqlalchemy/modelling.py
   :language: python
   :caption: modelling.py

The first element that we import is SQLAlchemy's :class:`Mapped <sqlalchemy.orm.Mapped>` class.

.. literalinclude:: /examples/plugins/sqlalchemy/modelling.py
   :language: python
   :emphasize-lines: 1
   :linenos:

``UUIDBase`` is a subclass of :class:`DeclarativeBase <sqlalchemy.orm.DeclarativeBase>`, and in addition to instrumenting
the class with SQLAlchemy's internals, it also gives us a ``UUID`` identity column, and automatic table name generation.

Did I mention that we love SQLAlchemy? We love it so much that we've included a suite of utilities for working with
SQLAlchemy in ``litestar.contrib.sqlalchemy``. One of these utilities is a ``Base`` class that we can use to declare our
models:

.. literalinclude:: /examples/plugins/sqlalchemy/modelling.py
   :language: python
   :emphasize-lines: 3
   :linenos:

``Base`` is a subclass of :class:`DeclarativeBase <sqlalchemy.orm.DeclarativeBase>`, and in addition to instrumenting
the class with SQLAlchemy's internals, it also gives us a ``UUID`` identity column, and automatic table name generation.

Then, we define our model:

.. literalinclude:: /examples/plugins/sqlalchemy/modelling.py
   :language: python
   :emphasize-lines: 6-8
   :linenos:

Here we have declared a ``TodoItem`` model, which has ``title`` and ``done`` attributes that should be mapped to columns
in the database.

The type of each database column is inferred from the Python type that is declared within each
:class:`Mapped <sqlalchemy.orm.Mapped>` annotation. So in this case, ``title`` will be ``VARCHAR`` and ``done`` will be
``INTEGER`` (some databases, such as PostgreSQL have a native boolean type, but many use ``1`` and ``0`` to represent
true and false, such as SQLite, which we'll be using in this tutorial).

.. tip::
    SQLAlchemy has very thorough documentation, ranging from tutorials aimed at beginners to a full set of reference
    docs. If you're new to SQLAlchemy, we recommend completing the
    `SQLAlchemy Unified Tutorial <https://docs.sqlalchemy.org/en/20/tutorial/index.html>`_.
