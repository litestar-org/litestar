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

+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
|      Function       |    Category    |                                                                                                                 Description                                                                                                                 |
+=====================+================+=============================================================================================================================================================================================================================================+
| ``get``             | Selecting Data | Select a single record by primary key. Raising an exception when no record is found.                                                                                                                                                        |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``get_one``         | Selecting Data | Select a single record specified by the ``kwargs`` parameters. An exception is raised when no record is found.                                                                                                                              |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``get_one_or_none`` | Selecting Data | Select a single record specified by the ``kwargs`` parameters. Returns ``None`` when no record is found.                                                                                                                                    |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``list``            | Selecting Data | Select a list of records specified by the ``kwargs`` parameters. Optionally it can be filtered by the included ``FilterTypes`` args.                                                                                                        |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``list_and_count``  | Selecting Data | Select a list of records specified by the ``kwargs`` parameters. Optionally it can be filtered by the included ``FilterTypes`` args. Results are returned as a 2 value tuple that includes the rows selected and the total count of records |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``get_or_create``   | Creating Data  | Get a record specified by the the ``kwargs`` parameters.  If no record is found, one is created with the given values.  There's an optional attribute to filter on a subset of the supplied parameters and to merge updates.                |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``create``          | Creating Data  | Create a new record in the database.                                                                                                                                                                                                        |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``create_many``     | Creating Data  | Create one or more rows in the database.                                                                                                                                                                                                    |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``update``          | Updating Data  | Update an existing record in the database.                                                                                                                                                                                                  |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``update_many``     | Updating Data  | Update one or more rows in the database.                                                                                                                                                                                                    |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``upsert``          | Updating Data  | A single operation that updates or inserts a record based whether or not the primary key value on the model object is populated.                                                                                                            |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``remove``          | Removing Data  | Remove a single record from the database.                                                                                                                                                                                                   |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``remove_many``     | Removing Data  | Remove one or more records from the database.                                                                                                                                                                                               |
+---------------------+----------------+---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------+


.. note::

    - All three of the bulk DML operations will leverage dialect specific enhancements to be as efficient as possible.  In addition to using efficient bulk inserts binds, the repository will optionally leverage the multi-row ``RETURNING`` support where possible.
    The repository will automatically detect this support from the SQL Alchemy driver, so no additional interaction is required to enable this.

    - SQL engines generally have a limit to the number of elements that can be appended into an `IN` clause.  The repository operations will automatically break lists that exceed this limit into multiple queries that are concatenated together before return.  You do not need to account for this in your own code.

Now that we have demonstrated how to interact with the repository objects outside of a Litestar application, let's use dependency injection to add this functionality to a Controller!
