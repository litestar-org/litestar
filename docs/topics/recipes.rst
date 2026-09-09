Recipes
=======

This section provides short, focused solutions to common questions and tasks when working
with Litestar. Each recipe addresses a specific scenario with a minimal working example.


.. _recipes-stacktrace:

Viewing the full stack trace inside route handlers
---------------------------------------------------

By default, Litestar catches exceptions raised inside route handlers and returns a JSON
error response without exposing the internal stack trace to the client. This is the
correct behaviour in production, but during development it makes it harder to see what
went wrong.

There are two complementary approaches to expose the full traceback while developing.

**Enable debug mode**

Pass ``debug=True`` when creating the application. In debug mode Litestar logs the full
traceback to the server's standard error stream and includes additional detail in the
HTTP error response:

.. code-block:: python

    from litestar import Litestar, get


    @get("/")
    async def index() -> str:
        raise ValueError("something went wrong")


    app = Litestar([index], debug=True)

You can also enable debug mode at runtime via the CLI ``--debug`` flag:

.. code-block:: shell

    litestar run --debug

or with the ``LITESTAR_DEBUG`` environment variable:

.. code-block:: shell

    LITESTAR_DEBUG=1 litestar run

**Drop into the debugger on exception**

If you want to interactively inspect the program state at the point the exception was
raised, use the ``pdb_on_exception`` option (see :doc:`/usage/debugging` for full
details):

.. code-block:: python

    app = Litestar([index], pdb_on_exception=True)

Or via the CLI:

.. code-block:: shell

    litestar run --pdb

.. note::

    Both ``debug`` and ``pdb_on_exception`` are intended for local development only.
    Do **not** enable them in production environments.
