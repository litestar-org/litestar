SQLAlchemy Plugin
=================

Starlite comes with built-in support for `SQLAlchemy <https://docs.sqlalchemy.org/>`_ via
the :class:`SQLAlchemyPlugin <starlite.plugins.sql_alchemy.SQLAlchemyPlugin>`.

Features
--------


* Managed `sessions <https://docs.sqlalchemy.org/en/14/orm/session.html>`_ (sync and async) including dependency injection
* Automatic serialization of SQLAlchemy models powered pydantic
* Data validation based on SQLAlchemy models powered pydantic

.. seealso::

    The following examples use SQLAlchemy's "2.0 Style" introduced in SQLAlchemy 1.4.

    If you are unfamiliar with it, you can find a comprehensive migration guide in SQLAlchemy's
    documentation `here <https://docs.sqlalchemy.org/en/14/changelog/migration_14.html#what-s-new-in-sqlalchemy-1-4>`_,
    and `a handy table <https://docs.sqlalchemy.org/en/14/changelog/migration_20.html#migration-orm-usage>`_
    comparing the ORM usage

.. attention::

    The :class:`SQLAlchemyPlugin <starlite.plugins.sql_alchemy.SQLAlchemyPlugin>` supports only
    `mapped classes <https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#declaring-mapped-classes>`_.
    `Tables <https://docs.sqlalchemy.org/en/14/tutorial/metadata.html#setting-up-metadata-with-table-objects>`_ are
    currently not supported since they are not easy to convert to pydantic models.

Basic Use
---------

You can simply pass an instance of :class:`SQLAlchemyPlugin` without passing config to the Starlite constructor. This will
extend support for serialization, deserialization and DTO creation for SQLAlchemy declarative models:

.. tab-set::

    .. tab-item:: Async
        :sync: async

        .. literalinclude:: /examples/plugins/sqlalchemy_plugin/sqlalchemy_async.py
            :caption: sqlalchemy_plugin.py
            :language: python


    .. tab-item:: Sync
        :sync: sync

        .. literalinclude:: /examples/plugins/sqlalchemy_plugin/sqlalchemy_sync.py
            :caption: sqlalchemy_plugin.py
            :language: python


.. admonition:: Using imperative mappings
    :class: info

    `Imperative mappings <https://docs.sqlalchemy.org/en/14/orm/mapping_styles.html#imperative-mapping>`_
    are supported as well, just make sure to use a mapped class instead of the table itself

    .. code-block:: python

        company_table = Table(
            "company",
            Base.registry.metadata,
            Column("id", Integer, primary_key=True),
            Column("name", String),
            Column("worth", Float),
        )


        class Company:
            pass


        Base.registry.map_imperatively(Company, company_table)


Relationships
-------------

.. attention::

    Currently only to-one relationships are supported because of the way the SQLAlchemy plugin handles relationships.
    Since it recursively traverses relationships, a cyclic reference will result in an endless loop. To prevent this,
    these relationships will be type as :class:`typing.Any` in the pydantic model
    Relationships are typed as :class:`typing.Optional` in the pydantic model by default so sending incomplete models
    won't cause any issues.


Simple relationships
^^^^^^^^^^^^^^^^^^^^

Simple relationships can be handled by the plugin automatically:

.. literalinclude:: /examples/plugins/sqlalchemy_plugin/sqlalchemy_relationships.py
    :caption: sqlalchemy_relationships.py
    :language: python


.. admonition:: Example
    :class: tip

    Run the above with ``uvicorn sqlalchemy_relationships:app``, navigate your browser to
    `http://127.0.0.0:8000/user/1 <http://127.0.0.0:8000/user/1>`_
    and you will see:

    .. code-block:: json

        {
          "id": 1,
          "name": "Peter",
          "company_id": 1,
          "company": {
            "id": 1,
            "name": "Peter Co.",
            "worth": 0
          }
        }


To-Many relationships and circular references
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For to-many relationships or those that contain circular references you need to define the pydantic models yourself:

.. literalinclude:: /examples/plugins/sqlalchemy_plugin/sqlalchemy_relationships_to_many.py
    :caption: sqlalchemy_relationships_to_many
    :language: python


.. admonition:: Example
    :class: tip

    Run the above with ``uvicorn sqlalchemy_relationships_to_many:app``, navigate your browser to `http://127.0.0.0:8000/user/1`_
    and you will see:

    .. code-block:: json

        {
          "id": 1,
          "name": "Peter",
          "pets": [
            {
              "id": 1,
              "name": "Paul"
            }
          ]
        }


Configuration
-------------

You can configure the Plugin using the :class:`SQLAlchemyConfig <starlite.plugins.sql_alchemy.SQLAlchemyConfig>` object.
