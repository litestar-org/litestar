=================
Application State
=================

Its possible to set & manipulate the Starlite application's `state` using a couple of
`application hooks`. We discussed more about these application hooks & the techniques to
use them in a later section of the documentations.

Hence for now, know that the main advantage of using the application ``state`` is its
accessibility during multiple stages of the connections. On top of it, the same ``state``
can be injected in to dependencies & route handlers. Since the said `application state` is
an instance & is accessible via the ``app.state`` attribute, as such it can be accessed
wherever the app instance is accessible.

Its important to understand in this context that the application instance is injected
into the ASGI ``scope`` mapping for each connection (i.e request or websocket connection)
as ``scope[app].state``. This makes the application accessible whenever the scope mapping
is available, e.g in middleware, on |Request|_ & |Websocket|_ instances (accessible as
``request.app`` & ``socket.app`` respectively) as well as many other places.

Therefore, `state` offers an easy way to share contextual data between disparate parts of
the application as described below:

.. literalinclude:: ../../examples/application_state/using_application_state.py

Initializing Application State
==============================

You can pass an object from which the application state will be instantiated using the
``initial_state`` keyword argument of the ``Starlite`` constructor:

.. literalinclude:: ../../examples/application_state/passing_initial_state.py

.. note::

   The ``initial_state`` can be a dictionary, an instance of |ImmutableState|_ or
   |State|_ or a list of tuples containing a bunch of key-value pairs.

.. important::

   Any value passed to ``initial_state`` will be deep copied to prevent mutation from
   outside the application context.

Injecting Application State Into Route Handlers & Dependencies
==============================================================

As seen in the example above, Starlite offers an easy way to inject state into route
handlers & dependencies. It does so by specifying ``state`` as a keyword argument to the
handler function. In other words, you can do the following inside a handler function or a
dependency to access the application state:

.. code-block:: python

    from starlite import get, State


    @get("/")
    def handler(state: State) -> None:
        ...

When using this pattern, you can specify the class to use for the ``state`` object. This
type isn't merely for type checking but Starlite will set a new `state instance` based on
the type you set there. This allows users to use custom classes for State!

But care should be taken since using state can lead to code which is difficult to reason
about & bugs which are difficult to understand due to changes in different ASGI contexts.
While manipulating state is very pwoerful, this pattern should only be used when its the
best choice & in certain limited fashion.

To discourage its usage, Starlite offers a builtin ``ImmutableState`` class which can be
used to type the `state` & ensure no mutation of state is allowed. Here is an example
showcasing the ``ImmutableState`` class & its usage:

.. literalinclude:: ../../examples/application_state/using_immutable_state.py


.. INFO: Necessary hack for creating a hyperlinked inline code. See this RST docs for
   more info - https://docutils.sourceforge.io/FAQ.html#is-nested-inline-markup-possible
.. |Request| replace:: ``Request``
.. _Request: ./reference/connection/1-request/#starlite.connection.request.Request

.. |Websocket| replace:: ``Websocket``
.. _Websocket: ./reference/connection/2-websocket/#starlite.connection.websocket.WebSocket

.. |ImmutableState| replace:: ``ImmutableState``
.. _ImmutableState: ./reference/datastructures/0-state/#starlite.datastructures.ImmutableState

.. |State| replace:: ``State``
.. _State: ./reference/datastructures/0-state/#starlite.datastructures.State
