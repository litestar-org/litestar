Adding Additional Features to the Repository
--------------------------------------------

While most of the functionality you need is built into the repository, there are still
cases where you need to add in additional functionality. Let's explore ways that we
can add functionality on top of the repository pattern.

.. tip:: The full code for this tutorial can be found below in the :ref:`Full Code <04-repo-full-code>` section.

Slug Fields
-----------

.. literalinclude:: /examples/sqla/sqlalchemy_repository_extension.py
    :language: python
    :caption: ``app.py``
    :lines: 10-23, 33-34, 37-42, 101-102, 106-108
    :linenos:

In this example, we are using a ``BlogPost`` model to hold blog post titles and
contents.  The primary key for this model is a ``UUID`` type. ``UUID`` and ``int`` are
good options for primary keys, but there are a number of reasons you may not want to use
them in your routes. For instance, it can be a security problem to expose integer-based
primary keys in the URL.  While UUIDs don't have this same problem, they are not
user-friendly or easy-to-remember, and create complex URLs. One way to solve this is to
add a user friendly unique identifier to the table that can be used for urls.  This is
often called a "slug".

First, we'll create a ``SlugKey`` field mixin that adds a text-based, URL-friendly,
unique column ``slug`` to the table. We want to ensure we create a slug value based on
the data passed to the ``title`` field.  To demonstrate what we are trying to
accomplish, we want a record that has a blog title of "Follow the Yellow Brick Road!"
to have the slugified value of "follow-the-yellow-brick-road".

.. literalinclude:: /examples/sqla/sqlalchemy_repository_extension.py
    :language: python
    :caption: ``app.py``
    :lines: 1-8, 14-23, 43-44, 46-100
    :linenos:

Since the ``BlogPost.title`` field is not marked as unique, this means that we'll have
to test the slug value for uniqueness before the insert.  If the initial slug is found,
a random set of digits are appended to the end of the slug to make it unique.

.. literalinclude:: /examples/sqla/sqlalchemy_repository_extension.py
    :language: python
    :caption: ``app.py``
    :lines: 1-23, 27-32, 101-102, 106-126, 170-180
    :linenos:

We are all set to use this in our routes now.  First, we'll convert our incoming
Pydantic model to a dictionary.  Next, we'll fetch a unique slug for our text.
Finally, we insert the model with the added slug.

.. note::

    Using this method does introduce an additional query on each insert. This should be
    considered when determining which fields actually need this type of functionality.

.. _04-repo-full-code:

Full Code
---------

.. dropdown:: Full Code (click to toggle)

    .. literalinclude:: /examples/sqla/sqlalchemy_repository_extension.py
        :language: python
        :caption: ``app.py``
        :emphasize-lines: 12, 37-42, 106-108, 177
        :linenos:
