ASGI Events & Application Hooks
===============================

In the previous introductory section of the documentations we briefly mentioned about the root
:class:`Starlite <starlite.app.Starlite>` class. This class accepts a bunch of `optional` arguments
& a couple of those arguments can be configured to control the behaviour of your Starlite application
based on certain ASGI events. This section of the documentations take a more deeper dive into how you
can use those hooks to configure your application throughout its lifespan.

About Application Hooks & Their Respective Events
-------------------------------------------------

All ASGI webservers (like `Uvicorn <https://www.uvicorn.org>`_ or
`Daphne <https://github.com/django/daphne>`_ & such) emits certain events through the lifespan of the
application they are invoked with. And Starlite can hook into those events to perform certain tasks as
intended for that particular event.

These hooks accepts a `list of callables` - either sync/async functions, methods or class instances &
you can pass those hooks as optional arguments to the ``Starlite`` instance. Two common examples of
such hooks are the :class:`on_startup <starlite.config.AppConfig.on_startup>` & the
:class:`on_shutdown <starlite.config.AppConfig.on_shutdown>` keyword arguments of the ``Starlite``
instance. And they will be called in order once the ASGI server emits the respective event.

The flowchart below is the best depiction of what a typical Starlite application's lifespan is like &
the hooks it triggers.

.. mermaid::
    :alt: Flow chart detailing the sequence of ASGI events & respective Starlite hooks

    flowchart LR
        Startup[ASGI-Event: lifespan.startup] --> before_startup --> on_startup --> after_startup
        Shutdown[ASGI_Event: lifespan.shutdown] --> before_shutdown --> on_shutdown --> after_shutdown

A typical real-world use case utilising these hooks would be for managing database connections to your
Starlite application. When you need to establish a database connection on application startup & close it
gracefully upon shutdown, these are the hooks which you'll need.

Here's an example code snippet showcasing this real-world scenario. It makes use of the async engine in
`SQLAlchemy <https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html>`_ to create a database
connection. Moreover, we create two functions - one to establish the connection & another to close the
connection. These functions will then be supplied to the ``Starlite`` constructor as showcased below:

.. literalinclude:: /examples/startup_and_shutdown.py
   :caption: Startup & Shutdown Events
   :language: python

The aforementioned ``on_startup`` & the ``on_shutdown`` were two simple hooks but Starlite provides
several such application level hooks. And in the next section of this documentation we'll take a more
detailed look at how we can use those hooks in your Starlite project.


Using Application Hooks the Right Way
-------------------------------------

TODO: Discuss how to use the hooks properly.
