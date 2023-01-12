=================
Application Hooks
=================

Starlite includes several application level hooks which allows an user to run their own
synchronous or asynchronous callable functions. While you're free to use these hooks as
you see fit, the design intention behind them is to allow easier instrumentation for
observability (monitoring, tracing, logging, etc).

.. note::

   All application hook keyword arguments detailed below receive a single callable or a
   single list of callables. If a list is provided, it is called in the order it is
   given.

Before & After Startup
============================

The ``before_startup`` & ``after_startup`` hooks take a
`sync/asyc handlers <./reference/types/1-callable-types/#starlite.types.LifeSpanHookHandler>`_
that receives the Starlite application as an argument & run during the ASGI startup
event. The callable is invoked respectively before or after the list of callables defined
in the ``on_startup`` list of callables.

.. literalinclude:: ../../examples/application_hooks/startup_hooks.py

Before & After Shutdown
============================

The ``before_shutdown`` & ``after_shutdown`` hooks are identical with the only difference
being the callable they receive is invoked before or after the list of callables defined
in the ``on_shutdown`` list of callables.

.. literalinclude:: ../../examples/application_hooks/shutdown_hooks.py

After Exception
============================

The ``after_exception`` hook takes a sync/async callable with three arguments passed to
it - the ``exception`` that occurred, the ASGI ``scope`` of the request or the websocket
connection & the application ``state``.

.. literalinclude:: ../../examples/application_hooks/after_exception_hook.py

.. important::

   This hook isn't meant to handle exceptions, rather it simply receives them to allow
   side effects. To handle exceptions you should define
   `exception handling <./usage/17-exceptions/#exception-handling>`_ instead.

Before Send
============================

The ``before_send`` hook takes a sync/async callable which is called when an ASGI message
is called. The hook receives the message instance & the application state.

.. literalinclude:: ../../examples/application_hooks/before_send_hook.py

Application Init
============================

Starlite includes a hook for intercepting the arguments passed to the Starlite constructor
before they're used to instantiate the application.

.. TODO: Figure out how to cross-reference sections of the "API Reference" docs.

Handlers can be passed to the ``on_app_init`` parameter on construction of the
application & in turn each will receive an instance of :class: `AppConfig <starlite.config.app.AppConfig>`
& must return an instance of the same.

This hook is useful for applying common configuration between applications & for use by
developers who may wish to develop third-party application configuration systems.

.. note::

   ``on_app_init`` handlers cannot be async functions as they're called within
   ``Starlite.__init__()`` which is outside of the async context.

.. literalinclude:: ../../examples/application_hooks/after_exception_hook.py

.. |AppConfig| replace:: ``AppConfig``
.. _AppConfig: ./reference/config/0-app-config/#starlite.config.app.AppConfig
