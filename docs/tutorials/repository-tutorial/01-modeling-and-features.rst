Database Modeling and Integrated Features
-----------------------------------------
In this section we will cover a basic introduction into the repository features.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_declarative_models.py
    :language: python
    :caption: app.py
    :emphasize-lines: 9, 8,19,20
    :linenos:

We are going to begin with a simple data modelling exercise using the included SQLAlchemy declarative model helpers.  The helpers, included as a set of model classes and mixins allow you to quickly enable common functionalities on your models.

Let's start by declaring a new model named ``Author`` using the :class:`UUIDBase <litestar.contrib.sqlalchemy.base.UUIDBase>` class.  We'll keep this first model limited to 3 fields: ``id``, ``name``, ``dob``.  This is all we need to create the ``author`` table.    

We'll continue by adding a simple ``Book`` relationship to the ``Author`` model.  We want to allow each author record to have zero to many book records.  To achieve this, we want to make sure each ``book`` record contains the ``author_id`` as a link.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_declarative_models.py
    :language: python
    :caption: app.py
    :emphasize-lines: 9, 21,26,27,28,29
    :linenos:

We'll use one additional feature when creating this new model - the automatically timestamped audit model.  This allows us to track when the record was inserted and lasted updated.  

Let's declare a new ``Book`` model using the :class:`UUIDAuditBase <litestar.contrib.sqlalchemy.base.UUIDAuditBase>` class.  Notice that the only change is the base class we inherit from.  This one change automatically adds the timestamp columns (``created`` and ``updated``) to the ``book`` table when deployed!

.. note::

    If you have a requirement to use integer based primary keys, identical implementations for the base model and base audit model available at :class:`BigIntBase <litestar.contrib.sqlalchemy.base.BigIntAuditBase>` and :class:`BigIntAuditBase <litestar.contrib.sqlalchemy.base.UUIDAuditBase>` respectively.

By using the built in base declarative models, you also inherit a few additional configurations that make working with your data easier:

- Synchronous and Asynchronous implementations tested with many popular database engines.  Currently 6 databases engines have been tested for support:  Postgres, SQLite, MySQL, DuckDB, Oracle, and Spanner
- Automatic table name inference from model name.  A model named ``EventLog`` translates to the the database table ``event_log``
- Custom :class:`GUID <litestar.contrib.sqlalchemy.types.GUID>` database that implements a native UUID in supported engines or a ``Binary(16)`` as a fallback.
- A :class:`BigIntIdentity <litestar.contrib.sqlalchemy.types.BigIntIdentity>` that reverts to an ``Integer`` for unsupported variants.
- A custom :class:`JSON <litestar.contrib.sqlalchemy.types.JSON>` that uses native ``JSONB`` where supported and ``Binary`` or ``Blob`` as a fallback.


That's the basics!  Let's expand on this an introduce the repository class.
