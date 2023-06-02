Interacting with repositories
-----------------------------
Now that we've covered the modelling basics, we are able to create our first repository class.  The repository classes includes all of the standard CRUD operations as well as a few advanced features such as pagination, filtering and bulk operations.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :language: python
    :caption: app.py
    :emphasize-lines: 14,70,71,72,73
    :linenos:

Here we import the :class:`SQLAlchemyAsyncRepository <litestar.contrib.sqlalchemy.repository.SQLAlchemyAsyncRepository>` class and create an ``AuthorRepository`` repository class.  This is all that's required to include all of the integrated repository features.

Next, we'll set up the dependency injection required for our repository.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :language: python
    :caption: app.py
    :emphasize-lines: 14,70,71,72,73
    :linenos:

TODO: Finally, we declare our ``AuthorController``.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :language: python
    :caption: app.py
    :emphasize-lines: 14,70,71,72,73
    :linenos:

TODO: Some notes about the controller here...

.. note::

    The ``list_and_count`` method is designed to be as efficient as possible.  Where possible, a windowed count function is used for paginated data.  This allows a single query to return the paginated data as well as the total count of records.  For databases that do not have support for the necessary analytic window functions, 2 queries are issued.  The first is for the paginated data and the second is the total count of records.


The above example used the asynchronous repository implementation, but we offer feature parity between the synchronous and async implementations.  Here's the synchronous version of this sample example:

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_sync_repository.py
    :language: python
    :caption: app.py
    :emphasize-lines:  
    :linenos:

You now have a feature complete CRUD service that includes pagination!  In the next section, we'll see how we can extend the built in repository to add additional functionality.