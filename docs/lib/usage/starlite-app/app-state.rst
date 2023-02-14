Application State
=================

The previous section about :doc:`Application Hooks </lib/usage/starlite-app/app-hooks>` briefly mentioned the usage of
application state in a Starlite project. And in this section of the documentations we will take a deeper look in to how
Starlite provides application state management capabilities.

Overview of Using State in a Starlite Application
-------------------------------------------------

The callables passed to the application hooks can receive an optional keyword argument called ``state`` and this is the
application's state object. This ``state`` object can not only be accessed in multiple stages of the connection but can
be injected into dependencies and route handlers as well.

The said application state is an instance of the :class:`State <starlite.datastructures.state.State>` datastructure. And
is accessible through the ``app.state`` attribute, as such it can be accessed wherever the ``app`` instance is
available.

The ``app`` instance is injected into the ASGI ``scope``, mapped for each connection (i.e `request` or `websocket`
connections) as ``scope["app"].state``. And this is how the ``app`` instance is accessible wherever the scope mapping
is available like in :doc:`middlewares </lib/usage/middleware/index>`, on
:class:`Request <starlite.connection.request.Request>` and :class:`WebSocket <starlite.connection.websocket.WebSocket>`
instances or among other places.

.. note::

   The ``Request`` and ``WebSocket`` instances are accessible through ``request.app`` or ``websocket.app``
   respectively.

We showcase how state offers an easy way to share contextual data between disparate parts of the application in the
example below:

.. literalinclude:: /examples/application_state/using_application_state.py
   :caption: Using Application State
   :language: python

Initialising Application State
------------------------------

TODO: Add content about initialising application state.

Injecting Application State into Route Handlers and Dependencies
----------------------------------------------------------------

TODO: Add content about injecting state into route handlers.
