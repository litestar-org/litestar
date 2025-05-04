Using the init plugin
---------------------

In our example application, we've seen that we need to manage the database engine within the scope of the application's
lifespan, and the session within the scope of a request. This is a common pattern, and the
:class:`SQLAlchemyInitPlugin <litestar.contrib.sqlalchemy.plugins.SQLAlchemyInitPlugin>` plugin provides assistance for
this.

In our latest update, we leverage two features of the plugin:

1. The plugin will automatically create a database engine for us and manage it within the scope of the application's
   lifespan.
2. The plugin will automatically create a database session for us and manage it within the scope of a request.

We access the database session via dependency injection, using the ``db_session`` parameter.

Here's the updated code:

.. literalinclude:: /examples/contrib/sqlalchemy/plugins/tutorial/full_app_with_init_plugin.py
    :language: python
    :linenos:
    :emphasize-lines: 12, 28, 76-78, 85

The most notable difference is that we no longer need the ``db_connection()`` lifespan context manager - the plugin
handles this for us. It also handles the creation of the tables in our database if we supply our metadata and
set ``create_all=True`` when creating a ``SQLAlchemyAsyncConfig`` instance.

Additionally, we have a new ``db_session`` dependency available to us, which we use in our ``provide_transaction()``
dependency provider, instead of creating our own session.

Next steps
==========

Next up, we'll make one final change to our application, and then we'll be recap!
