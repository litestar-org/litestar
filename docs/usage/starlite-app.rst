===============================
The Starlite Application Object
===============================

At the root of every Starlite application is an instance of the Starlite class.
Typically this code will be placed in a file called ``main.py`` at the project's root
directory.

Creating an app is straightforward - the only required args is a list of
`Controllers <1-routing/3-controllers>`_, `Routers <1-routing/2-routers>`_ or
`Route Handlers <./2-route-handlers/1-http-route-handlers>`_:

.. literalinclude:: ../../examples/hello_world.py

.. admonition:: Run It!

    Copy the code snippets to an example ``main.py`` file & run it using this command
    ``python main.py`` to get the following results:

    .. code-block:: console

        $ curl http://localhost:8000
        {"hello": "world"}

The app instance is the root level of the app - it has the base path of ``/`` and all root level
Controllers, Routers and Route Handlers should be registered on it.

.. admonition:: Learn More

   To learn more about registering routes, check out this chapter in the documentation:
   `Registering Routes <./1-routing/1-registering-routes>`_. See the `API Reference
   <reference/1-app/#starlite.app.Starlite>`_ for more details on the ``Starlite`` class
   & the ``kwargs`` it accepts.
