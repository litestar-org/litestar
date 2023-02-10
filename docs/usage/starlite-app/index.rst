The Starlite Application
========================

At the root of every Starlite project is an instance of the :class:`Starlite <starlite.app.Starlite>` class & this code
is generally placed in a file named `main.py` at the project's root directory.

.. note::
   Its just a standard practice to name the "root" Python file in a project as `main.py`. But you are free to name it
   anything else like `app.py` or something else.

That said, creating the root app is pretty straightforward and the only `required` argument is a list of
:class:`Controllers <.controller.Controller>`, :class:`Routers <.router.Router>` or
:class:`Route Handlers <.handlers.base.BaseRouteHandler>`. The later section of the documentation takes a more
comprehensive take on how to use the said class instances. But here's a quick peek into a simple standalone
Starlite application:

.. literalinclude:: /examples/hello_world.py
   :caption: A "Hello World" Starlite Project
   :language: python

The ``app`` instance is the root level of the app, as in, it has the base path of ``/``. And all root level Controllers,
Routers & Router Handlers should be registered on it.

.. seealso::
   You can learn more about registering routes at: :ref:`usage/routing:Registering Routes`

Starlite also provides additional functionalities like managing application state, handling static files, logging and much
more through this ``app`` instance as well. The next few chapters of the documentations will shed a more detailed look into
how you can use those functionalities in your Starlite project as well.

.. toctree::
   :titlesonly:

   app-hooks
   app-state
   static-files
   logging
   app-layers
