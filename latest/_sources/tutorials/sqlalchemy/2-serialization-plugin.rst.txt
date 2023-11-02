Using the serialization plugin
------------------------------

Our next improvement is to leverage the
:class:`SQLAlchemySerializationPlugin <litestar.contrib.sqlalchemy.plugins.SQLAlchemySerializationPlugin>`
so that we can receive and return our SQLAlchemy models directly to and from our handlers.

Here's the code:

.. literalinclude:: /examples/contrib/sqlalchemy/plugins/tutorial/full_app_with_serialization_plugin.py
    :language: python
    :linenos:
    :emphasize-lines: 10,77-78,82,84,88,92,99

We've simply imported the plugin and added it to our app's plugins list, and now we can receive and return our
SQLAlchemy data models directly to and from our handler.

We've also been able to remove the ``TodoType`` and ``TodoCollectionType`` aliases, and the ``serialize_todo()``
function, making the implementation even more concise.

Compare handlers before and after Serialization Plugin
======================================================

Once more, lets compare the sets of application handlers before and after our refactoring:

.. tab-set::

   .. tab-item:: After

        .. literalinclude:: /examples/contrib/sqlalchemy/plugins/tutorial/full_app_with_serialization_plugin.py
            :language: python
            :linenos:
            :lines: 76-100

   .. tab-item:: Before

        .. literalinclude:: /examples/contrib/sqlalchemy/plugins/tutorial/full_app_no_plugins.py
            :language: python
            :linenos:
            :lines: 70-102

Very nice! But, we can do better.

Next steps
==========

In our application, we've had to build a bit of scaffolding to integrate SQLAlchemy with our application. We've had to
define the ``db_connection()`` lifespan context manager, and the ``provide_transaction()`` dependency provider.

Next we'll look at how the :class:`SQLAlchemyInitPlugin <litestar.contrib.sqlalchemy.plugins.SQLAlchemyInitPlugin>` can
help us.
