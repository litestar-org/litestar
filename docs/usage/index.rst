================
The Starlite App
================

Application Object
==================

At the root of every Starlite application is an instance of the Starlite class.
Typically this code will be placed in a file called ``main.py`` at the project's root
directory.

Creating an app is straightforward - the only required args is a list of
`Controllers <1-routing/3-controllers>`_, `Routers <1-routing/2-routers>`_ or
`Route Handlers <./2-route-handlers/1-http-route-handlers>`_:

.. tab-set::

    .. tab-item:: Python 3.8+

        .. code-block:: python

            from typing import Dict

            from starlite import Starlite, get


            @get("/")
            def hello_world() -> Dict[str, str]:
                """Handler function that returns a greeting dictionary."""
                return {"hello": "world"}


            app = Starlite(route_handlers=[hello_world])


    .. tab-item:: Python 3.9+
        :sync: starlite

        .. code-block:: python

            from starlite import Starlite, get


            @get("/")
            def hello_world() -> dict[str, str]:
                """Handler function that returns a greeting dictionary."""
                return {"hello": "world"}


            app = Starlite(route_handlers=[hello_world])


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

Startup and Shutdown
====================

You can pass a list of `callables` - either synchrnous/asynchronous functions, methods or
class instances to the ``on_startup`` or ``on_shutdown`` keyword parameters of the
`Starlite instance <./reference/1-app/#starlite.app.Starlite>`_. Those will be called in
order, once the ASGI server (like ``uvicorn``, ``daphne``, etc) emits the respective
event.

Using Application State
=======================

Initialising Application State
------------------------------

Injecting Application State Into Route Handlers & Dependencies
--------------------------------------------------------------

Static Files
============

Sending Files as Attachments
----------------------------

File System Support & Cloud Files
---------------------------------

Logging
=======

Using Picologging
-----------------

Using StructLog
---------------

Subclass Logging Configs
------------------------

Application Hooks
=================

Before / After Startup
----------------------

After an Exception
------------------

Before Send
-----------

Application Initialization
--------------------------

Layered Architecture
====================
