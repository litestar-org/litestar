Application basics
==================

First steps
------------

Before we start building our TODO application, let's start with the basics.


Install Litestar
++++++++++++++++

To install Litestar, run ``pip install litestar[standard]``. This will install Litestar
as well as `uvicorn <https://www.uvicorn.org/>`_ -  a server that you can use to serve
your application.


Hello, world!
+++++++++++++

The most basic application one can implement and a classic is of course one that somehow
prints ``"Hello, world!"``:


.. literalinclude:: examples/hello_world.py
    :language: python
    :caption: app.py


Now save the contents of this example in a file called ``app.py`` and type
``litestar run`` in your terminal. This will serve the application locally on your
machine. Now visit http://127.0.0.1:8000/ in your browser:

.. image:: images/hello_world.png


Having a working application, let's examine how we got here in a bit more detail.


Route handlers
---------------

Route handlers are what you use to tell Litestar what functions to call when it receives
a request. They are called route handlers because they are usually serving a single
*route*, which in HTTP terms would be the *path*; The part of the URL that's specific
to you application.

The first argument to the route handler is the *path*, which in this example has been
set to ``/``. This means that the function ``hello_world`` will be called when a request
is being made to the ``/`` path of your application. The name of the handler decorator
- ``get`` - refers to the HTTP method which you want to respond to. Using ``get`` tells
Litestar that you only want to use this function when a ``GET`` request is being made.


.. literalinclude:: examples/hello_world.py
    :language: python
    :emphasize-lines: 4
    :linenos:


.. note::

    The syntax used in this example (the ``@get`` notation) is called a decorator. It's
    a function that takes another function as its argument (in this case ``hello_world``)
    and replaces it with the return value of the decorator function.
    Without the decorator, the example would look like this:

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


In this example, the ``hello_world`` function has a return annotation of ``-> str``.
This means that it will return a :class:`string <str>`, and lets Litestar know that
you'd like to send the return value as-is.

.. note::
    While type annotations by default don't have any influence on runtime behaviour,
    Litestar uses them for many things, for example to validate incoming request data.

    If you are using a static type checker such as
    `mypy <https://mypy.readthedocs.io/en/stable/>`_ or
    `pyright <https://microsoft.github.io/pyright/#/>`_ this has the added benefit of
    making your applications easy to check and more type safe.



Applications
------------

After a route handler has been defined, it needs to be registered with an application
in order to start serving requests. The application is an instance of the
:class:`Litestar <litestar.app.Litestar>` class. This is the entry point for everything,
and can be used to register previously defined route handlers by passing a list of them
as the first argument:

.. literalinclude:: examples/hello_world.py
    :language: python
    :emphasize-lines: 9
    :linenos:


.. seealso::
    :doc:`/usage/the-litestar-app`



Running the application
-----------------------

The last step is to actually run the application. Litestar does not include its own HTTP
server though but instead makes use of the
`ASGI protocol <https://asgi.readthedocs.io>`_, which is a protocol Python objects can
use in order to interact with application servers like
`uvicorn <https://www.uvicorn.org/>`_ that actually implement the HTTP protocol and
handle it for you.

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
