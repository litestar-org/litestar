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

To instantiate the application state, you need to pass an object using the
:class:`initial_state <starlite.config.AppConfig.initial_state>` keyword argument of the
:class:`Starlite <starlite.app.Starlite>` constructor. Here is an example code snippet showcasing the same:

.. literalinclude:: /examples/application_state/passing_initial_state.py
   :caption: Using Application State
   :language: python

.. note::

   The said values passed to the ``initial_state`` keyword argument can be either a dictionary, an instance of
   :class:`ImmutableState <starlite.datastructures.state.ImmutableState>` or
   :class:`State <starlite.datastructures.state.State>` or a list of tuples containing key-value pairs.

.. attention::
   Any value passed to the ``initial_state`` keyword argument will be deep copied to prevent mutation from outside the
   application context.

Now that we are well aware of how to initialise the application state, the next section delves in to the idea of
injecting the state into Route Handlers and Dependencies.

Injecting Application State into Route Handlers and Dependencies
----------------------------------------------------------------

The previous section shed some insight on how easy it is to inject the application state by simply passing a
parameter named ``state`` to the handler functions and dependencies. As a quick reminder, here is how you can inject
the application state to a handler function or a dependency:

.. code-block:: python

   from starlite import get, State


   @get("/")
   def handler(state: State) -> None:
       pass

When using this pattern its even possible to specify the class to use for the ``state`` object's type. Thereafter,
Starlite will utilise this type not only for type checking but for instantiating a new state instance as well. In other
words, its possible to use custom classes for the ``state`` like so:

.. TODO: Add the missing example here after further consultation

Although this feature can be very powerful, it can encourage users to follow anti-patterns. For example, misusing the
application state can lead to writing code which is difficult to reason about and debug. And this can often happen due
to changes in the different ASGI contexts. Hence, its **recommended** to use application state in a limited fashion and
only where it is absolutely necessary.

To discourage its usage, Starlite offers the builtin
:class:`ImmutableState <starlite.datastructures.state.ImmutableState>` class which ensures no mutation of state is
possible and is used for typing as well. Here is an example code snippet showcasing proper use of the
``ImmutableState`` class:

.. literalinclude:: /examples/application_state/using_immutable_state.py
   :caption: Using Custom State
   :language: python

Besides managing the application state, Starlite also provides handling static files as well! The next section takes a
deeper dive into how you can properly handle static files with Starlite.
