Interacting with repositories
-----------------------------
Now that we've covered the modelling basics, we are able to create our first repository class.  The repository classes includes all of the standard CRUD operations as well as a few advanced features such as pagination, filtering and bulk operations.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :language: python
    :caption: app.py
    :emphasize-lines: 14,70,71,72,73
    :linenos:

Here we import the :class:`SQLAlchemyAsyncRepository <litestar.contrib.sqlalchemy.repository.SQLAlchemyAsyncRepository>` class and create an ``AuthorRepository`` repository class.  This is all that's required to include all of the integrated repository features.

Lets look at these changes in more detail. What functionality are we gaining?

Selecting Data
--------------
- get
- get_one
- get_one_or_none
- list
- list_and_count

Creating Data
--------------
- get_or_create (with advanced ``upsert`` option)
- create
- create_many


Updating Data
--------------
- update
- update_many
- upsert


Deleting Data
--------------
- remove
- remove_many


.. note::

    Bulk operations with a returning clause are not supported for all database engines.  The repository operations will automatically detect the support from the SQL Alchemy driver, so no additional interaction is required to enable this.

    SQL engines generally have a limit to the number of elements that can be appended into an `IN` clause.  The repository operations will automatically break lists that exceed this limit into multiple queries that are concatenated together before return.  You do not need to account for this in your own code.

Now that we have demonstrated how to interact with the repository objects outside of a Litestar application, let's use dependency injection to add this functionality to a Controller!
