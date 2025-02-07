Working with Controllers and Repositories
-----------------------------------------
We've been working our way up the stack, starting with the database models, and now we
are ready to use the repository in an actual route.  Let's see how we can use this in a
controller.

.. tip:: The full code for this tutorial can be found below in the :ref:`Full Code <03-repo-full-code>` section.

First, we create a simple function that returns an instance of ``AuthorRepository``.
This function will be used to inject a repository instance into our controller routes.
Note that we are only passing in the database session in this example with no other
parameters.

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :language: python
    :caption: ``app.py``
    :lines: 25-28, 75-85
    :linenos:

Because we'll be using the SQLAlchemy plugin in Litestar, the session is automatically
configured as a dependency.

By default, the repository does not add any additional query options to your
base statement, but provides the flexibility to override it, allowing you to
pass your own statement:

.. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
    :language: python
    :caption: ``app.py``
    :lines: 9-11, 27-28, 81-95
    :linenos:

In this instance, we enhance the repository function by adding a ``selectinload``
option. This option configures the specified relationship to load via
``SELECT … IN …`` loading pattern, optimizing the query execution.

Next, we define the controller class ``AuthorController``. This controller
exposes five routes for interacting with the model ``Author``:

.. dropdown:: ``AuthorController`` (click to toggle)

    .. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
        :language: python
        :caption: ``app.py``
        :lines: 8, 11, 13-14, 16-17, 24, 119-202
        :linenos:

In our list detail endpoint, we use the pagination filter for limiting the amount of
data returned, allowing us to retrieve large datasets in smaller, more manageable chunks.

In the above examples, we've used the asynchronous repository implementation. However,
Litestar also supports synchronous database drivers with an identical implementation.
Here is a corresponding synchronous version of the previous example:

.. dropdown:: Synchronous Repository (click to toggle)

    .. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_sync_repository.py
        :language: python
        :caption: ``app.py``
        :linenos:

The examples above enable a feature-complete CRUD service that includes pagination! In
the next section, we'll explore how to extend the built-in repository to add additional
functionality to our application.

.. _03-repo-full-code:

Full Code
---------

.. dropdown:: Full Code (click to toggle)

    .. literalinclude:: /examples/contrib/sqlalchemy/sqlalchemy_async_repository.py
        :language: python
        :caption: ``app.py``
        :emphasize-lines: 77-80, 83-85, 90-95, 121-202
        :linenos:
