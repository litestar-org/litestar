Controllers and Repositories
----------------------------
We've been working our way up the stack, starting with the database models, and now we are ready to use the repository in an actual route.  Let's see how we can use this in a controller.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :language: python
    :caption: app.py
    :emphasize-lines: 76,77,78
    :linenos:

Here are creating a simple function that returns an instance of ``AuthorRepository``.  This function will be used to inject a repository instance into our controller routes.
Note that we are only passing in the database session in this example with no other parameters.
By default, the repository does not add any additional query options into your base statement.  However, you can easily override this by passing your own statement.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :language: python
    :caption: app.py
    :emphasize-lines: 82,83,84
    :linenos:

Here, we have added a ``selectinload`` option to ensure the necessary relationships are loaded with a `SELECT .. IN ...` loading pattern.

We'll declare the ``AuthorController`` to have 5 exposed routes for interacting with the model.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :language: python
    :caption: app.py
    :emphasize-lines: 110-183
    :linenos:

TODO: We use the pagination filter in the list detail endpoint.  make a not about the other

The above example used the asynchronous repository implementation, but we offer feature parity between the synchronous and async implementations.  Here's the synchronous version of this sample example:

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_sync_repository.py
    :language: python
    :caption: app.py
    :linenos:

You now have a feature complete CRUD service that includes pagination!  In the next section, we'll see how we can extend the built in repository to add additional functionality.
