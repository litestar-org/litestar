Final touches and recap
-----------------------

There is one more improvement that we can make to our application. Currently, we utilize both the
:class:`SQLAlchemyInitPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemyInitPlugin>` and the
:class:`SQLAlchemySerializationPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemySerializationPlugin>`, but there
is a shortcut for this configuration: the
:class:`SQLAlchemyPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemyPlugin>` is a combination of the two, so we
can simplify our configuration by using it instead.

Here is our final application:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :emphasize-lines: 10, 82

Recap
=====

In this tutorial, we have learned how to use the SQLAlchemy plugin to create a simple application that uses a database
to store and retrieve data.

In the final application ``TodoItem`` is defined, representing a TODO item. It extends from the
:class:`DeclarativeBase <sqlalchemy.orm.DeclarativeBase>` class provided by `SQLAlchemy <http://www.sqlalchemy.org/>`_:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-6, 12-21

Next, we define a dependency that centralizes our database transaction management and error handling. This dependency
depends on the ``db_session`` dependency, which is provided by the SQLAlchemy plugin, and is made available to our
handlers via the ``transaction`` argument:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-11, 22-32

We also define a couple of utility functions, that help us to retrieve our TODO items from the database:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-11, 33-50

We define our route handlers, which are the interface through which TODO items can be created, retrieved and updated:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-11, 51-69

Finally, we define our application, using the
:class:`SQLAlchemyPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemyPlugin>` to configure SQLAlchemy and manage the
engine and session lifecycle, and register our ``transaction`` dependency.

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_plugin.py
    :language: python
    :linenos:
    :lines: 1-11, 78-83

.. seealso::

    * `Advanced Alchemy Documentation <https://advanced-alchemy.litestar.dev/>`_
