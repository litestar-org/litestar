CLI
===

Starlite optionally provides a simple command line interface, for running and managing
Starlite applications, powered by `click <https://click.palletsprojects.com/>`_ and
`rich <https://rich.readthedocs.io>`_.

Enabling the CLI
----------------

Dependencies for the CLI are not included by default, to keep the packages needed to install
Starlite to a minimum. To enable the CLI, Starlite has to be installed with the ``cli`` or ``standard``
extra:

.. code-block:: shell

   pip install starlite[cli]

.. code-block:: shell

   pip install starlite[standard]

After installing any of these two, the ``starlite`` command will be available as the entrypoint
to the CLI.

Autodiscovery
-------------

Starlite will automatically discover Starlite applications and application factories in
certain places:

1. ``app.py``
2. ``application.py``
3. ``asgi.py``
4. ``app/__init__.py``

If any of these files contains an instance of the :class:`Starlite <.app.Starlite>` class, a function named
``create_app``, or a function annotated as returning a :class:`Starlite <.app.Starlite>` instance, the CLI will pick it up.

Commands
--------

Starlite
^^^^^^^^

The ``starlite`` command is the main entrypoint to the CLI. If the ``--app`` flag is not passed,
the app will be automatically discovered as described in `the section above <autodiscovery>`_

Options
~~~~~~~

+-----------+---------------------------+---------------------------------------------+
| Flag      | Environment variable      | Description                                 |
+===========+===========================+=============================================+
| ``--app`` | ``STARLITE_APP``          | ``<modulename>.<submodule>:<app instance>`` |
+-----------+---------------------------+---------------------------------------------+


Run
^^^

The ``run`` command runs a Starlite application using `uvicorn <https://www.uvicorn.org/>`_.

.. code-block:: shell

   starlite run

.. caution::

    This feature is intended for development purposes only and should not be used to
    deploy production applications

.. _cli-run-options:

Options
~~~~~~~

+------------------------+---------------------------+-----------------------------------------------------------------+
| Flag                  | Environment variable      | Description                                                      |
+========================+======================+======================================================================+
| ``-r``\ , ``--reload`` | ``STARLITE_RELOAD``       |  Reload the application when files in its directory are changed |
+------------------------+---------------------------+-----------------------------------------------------------------+
| ``-p``\ , ``--port``   | ``STARLITE_PORT``         | Bind the the server to this port [default: 8000]                |
+------------------------+---------------------------+-----------------------------------------------------------------+
| ``--host``             | ``STARLITE_PORT``         | Bind the server to this host [default: 127.0.0.1]               |
+------------------------+---------------------------+-----------------------------------------------------------------+
| ``--debug``            | ``STARLITE_DEBUG``        | Run the application in debug mode                               |
+------------------------+---------------------------+-----------------------------------------------------------------+
| ``--debug``            | ``STARLITE_DEBUG``        | Run the application in debug mode                               |
+------------------------+---------------------------+-----------------------------------------------------------------+


Info
^^^^

The ``info`` command displays useful information about the selected application and its configuration

.. code-block:: shell

   starlite info


.. image:: /images/cli/starlite_info.png
   :alt: starlite info


Routes
^^^^^^

The ``routes`` command displays a tree view of the routing table

.. code-block:: shell

   starlite routes


.. image:: /images/cli/starlite_routes.png
   :alt: starlite info


Sessions
^^^^^^^^

This command and its subcommands provide management utilities for
:ref:`server-side session backends <usage/middleware/builtin-middleware:server-side sessions>`.

Delete
~~~~~~

The ``delete`` subcommand deletes a specific session from the backend.

.. code-block:: shell

   starlite sessions delete cc3debc7-1ab6-4dc8-a220-91934a473717

Clear
~~~~~

The ``clear`` subcommand clears all sessions from the backend.

.. code-block:: shell

   starlite sessions clear

OpenAPI
^^^^^^^

This command provides utilities to generate OpenAPI schema and TypeScript types.

Schema
~~~~~~

The ``schema`` subcommand generates OpenAPI specs from the Starlite application, serializing these as either JSON or YAML.
The serialization format depends on the filename, which is by default ``openapi_schema.json``. You can specify a different
filename using the ``--output`` flag. For example:

.. code-block:: shell

   starlite openapi schema --output my-specs.yaml

TypeScript
~~~~~~~~~~

The ``typescript`` subcommand generates TypeScript definitions from the Starlite application's OpenAPI specs.  For example:

.. code-block:: shell

   starlite openapi typescript

By default, this command will output a file called ``api-specs.ts``. You can change this using the ``--output`` option:

.. code-block:: shell

   starlite openapi typescript --output my-types.ts

You can also specify the top level TypeScript namespace that will be created, which by default will be called API:

.. code-block:: typescript

   export namespace API {
       // ...
   }

To do this use the ``--namespace`` option:

.. code-block:: shell

   starlite openapi typescript --namespace MyNamespace

Which will result in:

.. code-block:: typescript

   export namespace MyNamespace {
       // ...
   }

Extending the CLI
-----------------

Starlite's CLI is built with `click <https://click.palletsprojects.com/>`_\ , and can be easily extended.
All that's needed to add subcommands under the ``starlite`` command is adding an
`entry point <https://packaging.python.org/en/latest/specifications/entry-points/>`_\ , pointing
to a :class:`click.Command <click.Command>` or :class:`click.Group <click.Group>`, under the
``starlite.commands`` group.

.. tab-set::

    .. tab-item:: setup.py

        .. code-block:: python

           from setuptools import setup

           setup(
               name="my-starlite-plugin",
               ...,
               entry_points={
                   "starlite.commands": ["my_command=my_starlite_plugin.cli:main"],
               },
           )



    .. tab-item:: poetry

        .. code-block:: toml

           [tool.poetry.plugins."starlite.commands"]
           my_command = "my_starlite_plugin.cli:main"



Accessing the app instance
^^^^^^^^^^^^^^^^^^^^^^^^^^

When extending the Starlite CLI, you most likely need access to the loaded ``Starlite`` instance.
This can be achieved by adding the special ``app`` parameter to your CLI functions. This will cause
``Starlite`` instance to be injected into the function whenever it is being called from a click-context.

.. code-block:: python

   import click
   from starlite import Starlite


   @click.command()
   def my_command(app: Starlite) -> None: ...
