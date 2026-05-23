Using the serialization plugin
------------------------------

Our next improvement is to leverage the
:class:`SQLAlchemySerializationPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemySerializationPlugin>`
so that we can receive and return our SQLAlchemy models directly to and from our handlers.

Here's the code:

.. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_serialization_plugin.py
    :language: python
    :linenos:
    :emphasize-lines: 12, 75-77, 80-83, 86-91, 98

We've simply imported the plugin and added it to our app's plugins list, and now we can receive and return our
SQLAlchemy data models directly to and from our handler.

We've also been able to remove the ``TodoType`` and ``TodoCollectionType`` aliases, and the ``serialize_todo()``
function, making the implementation even more concise.

Compare handlers before and after Serialization Plugin
======================================================

Once more, let's compare the sets of application handlers before and after our refactoring:

.. tab-set::

   .. tab-item:: After

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_with_serialization_plugin.py
            :language: python
            :linenos:
            :lines: 1-13, 73-99

   .. tab-item:: Before

        .. literalinclude:: /examples/plugins/sqlalchemy_init_plugin/full_app_no_plugins.py
            :language: python
            :linenos:
            :lines: 1-12, 67-100

Very nice! But, we can do better.

Next steps
==========

In our application, we've had to build a bit of scaffolding to integrate SQLAlchemy with our application. We've had to
define the ``db_connection()`` lifespan context manager, and the ``provide_transaction()`` dependency provider.

Next we'll look at how the :class:`SQLAlchemyInitPlugin <advanced_alchemy.extensions.litestar.plugins.SQLAlchemyInitPlugin>` can
help us.
