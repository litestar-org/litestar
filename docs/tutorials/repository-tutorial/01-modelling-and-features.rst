Introduction to Database Modelling and Repository Features
----------------------------------------------------------
In this tutorial, we will cover the integrated repository features in Litestar, starting
with database modelling using the included SQLAlchemy declarative model helpers. These
are a series of classes and mixins that incorporate commonly used functions/column types
to make working with models easier.

.. tip:: The full code for this tutorial can be found below in the :ref:`Full Code <01-repo-full-code>` section.

Modelling
---------

We'll begin by modelling the entities and relationships between authors and books.
We'll start by creating the ``Author`` table, utilizing the
:class:`UUIDBase <advanced_alchemy.base.UUIDBase>` class. To keep things
simple, our first model will encompass only three fields: ``id``, ``name``, and ``dob``.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_declarative_models.py
    :language: python
    :caption: ``app.py``
    :lines: 9, 11, 17-20
    :linenos:

The book entity is not considered a "strong" entity and therefore always requires an
author to be created.  We need to configure our SQLAlchemy classes so that it is aware
of this relationship. We will extend the ``Author`` model by incorporating a ``Book``
relationship. This allows each ``Author`` record to possess multiple ``Book`` records.
By configuring it this way, SQLAlchemy will automatically include the necessary foreign
key constraints when using the ``author_id`` field in each ``Book`` record.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_declarative_models.py
    :language: python
    :caption: ``app.py``
    :lines: 9, 11, 17-22, 27-30
    :linenos:

By using the audit model, we can automatically record the time a record was created and
last updated.

To implement this, we will define a new ``Book`` model via the
:class:`UUIDAuditBase <advanced_alchemy.base.UUIDAuditBase>` class. Observe
that the only modification here is the parent class from which we inherit. This minor
change endows the `book` table with automatic timestamp columns
(`created` and `updated`) upon deployment!

.. note::

    If your application requires integer-based primary keys, equivalent base model
    and base audit model implementations can be found at
    :class:`BigIntBase <advanced_alchemy.base.BigIntAuditBase>` and
    :class:`BigIntAuditBase <advanced_alchemy.base.UUIDAuditBase>`
    respectively.

.. important::
    `Spanner <https://cloud.google.com/spanner>`_ only:

    Using monotonically changing primary keys is considered an
    anti-pattern in Spanner and leads to performance problems. Additionally, Spanner
    does not currently include an idiom comparable to the ``Sequence`` object.  This
    means the ``BigIntBase`` and ``BigIntAuditBase`` are not currently supported for
    Spanner.

Additional features provided by the built-in base models include:

- Synchronous and Asynchronous repository implementations have been tried and tested
  with various popular database engines. As of now, six database engines are supported:
  Postgres, SQLite, MySQL, DuckDB, Oracle, and Spanner.
- Automatic table name deduction from model name. For instance, a model named
  ``EventLog`` would correspond to the ``event_log`` database table.
- A :class:`GUID <advanced_alchemy.types.GUID>` database type that
  establishes a native UUID in supported engines or a ``Binary(16)`` as a fallback.
- A ``BigInteger`` variant
  :class:`BigIntIdentity <advanced_alchemy.types.BigIntIdentity>` that
  reverts to an ``Integer`` for unsupported variants.
- A custom :class:`JsonB <advanced_alchemy.types.JsonB>` type that uses
  native ``JSONB`` where possible and ``Binary`` or ``Blob`` as an alternative.
- A custom :class:`EncryptedString <advanced_alchemy.types.EncryptedString>` encrypted string that supports multiple cryptography backends.

Let's build on this as we look at the repository classes.

.. _01-repo-full-code:

Full Code
---------

.. dropdown:: Full Code (click to toggle)

    .. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_declarative_models.py
        :language: python
        :caption: ``app.py``
        :emphasize-lines: 9, 18-21, 27-30
        :linenos:
