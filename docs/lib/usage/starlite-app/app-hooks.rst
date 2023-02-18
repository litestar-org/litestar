ASGI Events and Application Hooks
===============================

In the previous introductory section of the documentations we briefly mentioned about the root
:class:`Starlite <starlite.app.Starlite>` class. This class accepts several `optional` arguments
and a couple of those arguments can be configured to control the behavior of your Starlite application
. This section of the documentations take a deeper dive into how you
can use these hooks to configure your application throughout its lifespan.

Application Hooks Overview
-------------------------------------------------------------

ASGI webservers (like `Uvicorn <https://www.uvicorn.org>`_ or
`Daphne <https://github.com/django/daphne>`_ and such) emits certain events through the lifespan of the
application they are invoked with. And Starlite can hook into those events to perform certain tasks as
intended for that particular event.

These hooks accepts a `list of callables` - either sync/async functions, methods or class instances and
you can pass those hooks as optional arguments to the ``Starlite`` instance. Two common examples of
such hooks are the :class:`on_startup <starlite.config.AppConfig.on_startup>` and the
:class:`on_shutdown <starlite.config.AppConfig.on_shutdown>` keyword arguments of the ``Starlite``
instance. And they will be called in order once the ASGI server emits the respective event.

The flowchart below is the best depiction of what a typical Starlite application's lifespan is like and
the hooks it triggers.

.. mermaid::
    :alt: Flow chart detailing the sequence of ASGI events and respective Starlite hooks

    flowchart LR
        Startup[ASGI-Event: lifespan.startup] --> before_startup --> on_startup --> after_startup
        Shutdown[ASGI_Event: lifespan.shutdown] --> before_shutdown --> on_shutdown --> after_shutdown

A typical real-world use case utilising these hooks would be for managing database connections to your
Starlite application. When you need to establish a database connection on application startup and close it
gracefully upon shutdown, these are the hooks which you will need.

Here's an example code snippet showcasing this real-world scenario. It makes use of the async engine in
`SQLAlchemy <https://docs.sqlalchemy.org/en/latest/orm/extensions/asyncio.html>`_ to create a database
connection. Moreover, we create two functions - one to establish the connection and another to close the
connection. These functions will then be supplied to the ``Starlite`` constructor as showcased below:

.. literalinclude:: /examples/startup_and_shutdown.py
   :caption: Startup and Shutdown Events
   :language: python

The aforementioned ``on_startup`` and the ``on_shutdown`` were two simple hooks but Starlite provides
several such application level hooks. And in the next section of this documentation we will take a more
detailed look at how we can use those hooks in your Starlite project.


Real World Use Case of Starlite Application Hooks
-------------------------------------------------

The previous section of this article shed light on to two of the most commonly used hooks in a typical
Starlite application. But Starlite includes more such application level hooks for various purposes and we will discuss
some of those use cases in this section of the article. Similar to the two example hooks described in the
aforementioned section, the other hook Starlite provides also allows the user to run their own sync/async callables.

The Starlite hooks are also designed in a manner so as to allow easy instrumentation for observability like monitoring,
tracing, logging and such. So without further adieu, let's take a look at some real-world code snippets showcasing these
Starlite hooks.

.. note::

   All application hook keyword arguments detailed below receive either a single callable or a list of callables. If a
   list is provided, it is called in the order it is provided.

Before and After Startup
^^^^^^^^^^^^^^^^^^^^^^

To configure your application to behave in certain ways before and after it starts, Starlite provides the handy
:class:`before_startup <starlite.config.AppConfig.before_startup>` and the
:class:`after_startup <starlite.config.AppConfig.after_startup>` hooks. These hooks accepts a sync/async callable as
arguments and are invoked during the ASGI startup event. Hence, the callable is invoked before or after the list of
callables which are passed to the ``on_startup`` hook.

.. note::

   See the example above in the previous section to learn more about using the ``on_startup`` hook.

That said, here's an example code snippet to showcase the ``before_startup`` and ``after_startup`` hooks in action:

.. literalinclude:: /examples/application_hooks/startup_hooks.py
   :caption: Before and After Startup Hooks
   :language: python

Before and After Shutdown
^^^^^^^^^^^^^^^^^^^^^^^

Somewhat similar to the previously mentioned ``before_startup`` and ``after_startup`` hooks, there are the
:class:`before_shutdown <starlite.config.AppConfig.before_shutdown>` and the
:class:`after_shutdown <starlite.config.AppConfig.after_shutdown>` hooks as well. These hooks, as their name suggests
are invoked before or after the ASGI shutdown event. The callables they receive as arguments are invoked after the
callables which are passed to the ``on_shutdown`` hook.

Here is a code snippet for better understanding of how these hooks are supposed to work:

.. literalinclude:: /examples/application_hooks/shutdown_hooks.py
   :caption: Before and After Shutdown Hooks
   :language: python

After Exception
^^^^^^^^^^^^^^^

The :class:`after_exception <starlite.config.AppConfig.after_exception>` hook is slightly different from the others in
context to its usage. It accepts a callable which in turn is called with three arguments:

* The ``exception`` which has occurred.
* The ASGI ``scope`` of the request or the websocket connection.
* The application ``state``.

For a better understanding of the hook, here's a simple example showcasing it:

.. literalinclude:: /examples/application_hooks/after_exception_hook.py
   :caption: After Exception Hook
   :language: python

.. attention::
   This hook is not meant to handle exceptions! It simply receives the raised exception to perform some other side
   effects based on them. For handling exceptions, refer to the
   :ref:`exception handlers </lib/usage/exceptions:exception-handling>` section of the documentations.

Before Send
^^^^^^^^^^^

The :class:`before_send <starlite.config.AppConfig.before_send>` hook takes a sync/async callable as well like the rest
of the hooks but its arguments are invoked when an ASGI message is sent. The parameters of this hook are:

* The ASGI message instance.
* The application state.

.. note::

   We discuss more about the `application state` in the next section of the documentations.

Here's an example code snippet to showcase using the hook in a Starlite application.

.. literalinclude:: /examples/application_hooks/before_send_hook.py
   :caption: Before Send Hook
   :language: python

Application Init
^^^^^^^^^^^^^^^^

Starlite also provides a hook for intercepting the arguments passed to the :class:`Starlite <starlite.app.Starlite>`
constructor as well. This hook is used to instantiate the application before the arguments are even invoked. Handler
functions can be passed to the :class:`on_app_init <starlite.config.AppConfig.on_app_init>` parameter on construction
of the application. And this in turn will receive an instance of :class:`AppConfig <starlite.config.AppConfig>` which
must return an instance of the same as well.

This hook is useful in scenarios like:

* Applying common configurations between applications.
* Developing third-party application configuration systems.

.. important::

   The ``on_app_init`` handler functions should not be async functions since they are called within the context of
   :class:`Starlite.__init__() <starlite.app.Starlite.__init__>` (which is outside of an async context).

That said, here is an example code snippet to shed better light on using the hook properly:

.. literalinclude:: /examples/application_hooks/on_app_init.py
   :caption: Application Initialisation Hook
   :language: python
