Introduction
------------

Here is a full script that shows how you can use SQLAlchemy with Litestar. In this app, we interacting with SQLAlchemy
in the manner described by the
`SQLAlchemy documentation <https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#synopsis-orm>`_, and so if you
are looking for more information about any of the SQLAlchemy code, this will be a great place to start.

Beyond that, we use a couple of Litestar features that we haven't looked at yet:

1. Management and injection of application state
2. Lifespan context managers

And we will continue to learn about other Litestar features as we work through the tutorial, such as:

1. Dependency injection
2. Data Transfer Objects
3. Plugins

The full app
============

While it may look imposing, this app only has minor behavioral differences to the previous example. It is still an app
that maintains a TODO list, that allows for adding, updating and viewing the collection of TODO items.

Don't worry if there are things in this example that you don't understand. We will cover all of the components in detail
in the following sections.

.. literalinclude::
    /examples/contrib/sqlalchemy/plugins/tutorial/full_app_no_plugins.py
    :language: python
    :linenos:

The differences
===============

Apart from the obvious differences due to the SQLAlchemy code, there are a few things worth mentioning from the outset.

Complexity
++++++++++

This code is undoubtedly more complex than the code we have seen so far - although a crude measure of complexity, we can
see that there are more than double the lines of code to the previous example.

Lifespan context manager
++++++++++++++++++++++++

When using a database, we need to ensure that we clean up our resources correctly. To do this, we create a context
manager called ``db_connection()`` that creates a new :class:`engine <sqlalchemy.ext.asyncio.AsyncEngine>` and disposes
of it when we are done. This context manager is added to the applicaton's ``lifespan`` argument.

.. literalinclude::
    /examples/contrib/sqlalchemy/plugins/tutorial/full_app_no_plugins.py
    :language: python
    :linenos:
    :lines: 29-41,100

Application state
+++++++++++++++++

We see two examples of access and use of application state in this example. The first is in the ``db_connection()``
context manager, where we use the ``app.state`` object to store the engine.

.. literalinclude::
    /examples/contrib/sqlalchemy/plugins/tutorial/full_app_no_plugins.py
    :language: python
    :linenos:
    :lines: 29-41
    :emphasize-lines: 3,6

The second is by using the ``state`` keyword argument in our handler functions, so that we can access the engine in our
handlers.

.. literalinclude::
    /examples/contrib/sqlalchemy/plugins/tutorial/full_app_no_plugins.py
    :language: python
    :linenos:
    :lines: 67-72
    :emphasize-lines: 2,3

Serialization
+++++++++++++

Now that we are using SQLAlchemy models, Litestar cannot automatically handle (de)serialization of our data. We have
to convert the SQLAlchemy models to a type that Litestar can serialize. This example introduces two type aliases,
``TodoType`` and ``TodoCollectionType`` to help us represent this data at the boundaries of our handlers. It also
introduces the ``serialize_todo()`` to help us convert our data to and from the ``TodoItem`` type.

.. literalinclude::
    /examples/contrib/sqlalchemy/plugins/tutorial/full_app_no_plugins.py
    :language: python
    :linenos:
    :lines: 2-3,14-16,45-48,89-98
    :emphasize-lines: 3,4,7,8,12,18

Behavior
++++++++

the ``add_item()`` and ``update_item()`` routes no longer return the full collection, instead they return the item that
was added or updated. This is a minor detail change, but it is worth noting as it brings the behavior of the app closer
to what we would expect from a conventional API.

Next steps
==========

Lets start cleaning this app up a little.

One of the niceties that we've lost in this example is being able to receive and return data to/from our handlers as
instances of our data model. In the original TODO application, we modelled with Python dataclasses which are natively
supported for (de)serialization by Litestar. In the next section, we will look at how we can get this functionality
back!
