Application basics
==================

In the previous example we got a basic application running that makes our browser
display a greeting. Let's examine how we got there.

Route handlers
---------------

Route handlers are the way we use to tell Litestar how we want our functions to interact
with the application. They are called route handlers because they are usually serving a
single *route*, which in HTTP terms would be the *path*; The part of the URL that's
specific to our application.

The first argument to the route handler is the *path*, which we set to ``/``. This means
that our function ``hello_world`` will be called when someone accesses the ``/`` path
of our application. The name of the handler decorator - ``get`` - refers to the HTTP
method which we want to use. Using ``get`` tells Litestar that we only want to use this
function when a ``GET`` request is being made.


.. literalinclude:: examples/hello_world.py
    :language: python
    :emphasize-lines: 4
    :linenos:


.. note::

    The syntax used in this example (the ``@get`` notation) is called a decorator. It's
    a function that takes another function as its argument (in this case ``hello_world``)
    and replaces it with the return value of the decorator function.
    Without the decorator, our example would look like this:

    .. code-block:: python

        async def hello_world() -> str:
            return "Hello, world!"


        hello_world = get("/")(hello_world)

    For an in-depth explanation of decorators, you can read this excellent Real Python
    article: https://realpython.com/primer-on-python-decorators/


.. seealso::
    :doc:`/usage/route-handlers`


Type annotations
----------------

Type annotations play an important role in a Litestar application. They tell Litestar
how you want your data to behave, and what you intend to do with it.


.. literalinclude:: examples/hello_world.py
    :language: python
    :emphasize-lines: 5
    :linenos:


In this example we have annotated our ``hello_world`` function with ``-> str``. This
means that it will return a :class:`string <str>`, and let's Litestar know that we'd
like to send the return value as-is.

.. note::
    While type annotations usually don't have any influence on runtime behaviour,
    Litestar uses them for many things, for example to validate incoming request data.

    If you are using a static type checker such as
    `mypy <https://mypy.readthedocs.io/en/stable/>`_ or
    `pyright <https://microsoft.github.io/pyright/#/>`_ this has the added benefit of
    making your applications easy to check.



Applications
------------

The last step is to create an application object; An instance of the
:class:`Litestar <litestar.app.Litestar>` class. This is the entry point for everything,
and we can use it to register our previously defined route handlers by passing a list
of them as the first argument to the class:

.. literalinclude:: examples/hello_world.py
    :language: python
    :emphasize-lines: 9
    :linenos:


.. seealso::
    :doc:`/usage/the-litestar-app`



Running the application
-----------------------

As we learned in the previous step, Litestar itself is simply a Python object. This in
itself is not enough to be able to communicate using the language of the web: HTTP. For
that we need a dedicated program: An application server.
`uvicorn <https://www.uvicorn.org/>`_ is an example of this. It enables us to pass it
our application and serve it via HTTP.

If you installed Litestar with ``pip install litestar[standard]``, this will have
included *uvicorn*, as well as the Litestar CLI. The CLI provides a convenient wrapper
around uvicorn, allowing you to easily run applications without the need for much
configuration.

When you run ``litestar run``, it will recognise the ``app.py`` file and the
``Litestar`` instance within it without the need to specify this manually.

.. tip::
    You can start the server in "reload mode", which will reload the application each
    time you have made a change to the file. For this, simply pass the ``--reload``
    flag as a command line argument: ``litestar run --reload``.



.. seealso::
    :doc:`/usage/cli`
