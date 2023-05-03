CLI
===

Litestar optionally provides a simple command line interface, for running and managing
Litestar applications, powered by `click <https://click.palletsprojects.com/>`_ and
`rich <https://rich.readthedocs.io>`_.

Enabling the CLI
----------------

Dependencies for the CLI are not included by default, to keep the packages needed to install
Litestar to a minimum. To enable the CLI, Litestar has to be installed with the ``cli`` or ``standard``
extra:

.. code-block:: shell

   pip install litestar[cli]

.. code-block:: shell

   pip install litestar[standard]

After installing any of these two, the ``litestar`` command will be available as the entrypoint
to the CLI.

Autodiscovery
-------------

Litestar will automatically discover Litestar applications and application factories placed within the canonical modules
``app`` and ``application``, which can be singular files or directories. Within those modules, or submodules thereof,
the CLI will pick up any :class:`Litestar <.app.Litestar>` instance, callables named ``create_app``, or callables
annotated as returning a :class:`Litestar <.app.Litestar>` instance.

The lookup will consider these locations in order:

1. ``app.py``
2. ``app/__init__.py``
3. Submodules of ``app``
4. ``application.py``
5. ``application/__init__.py``
6. Submodules ``application``

and within those, look for:

1. An object named ``app`` that's an instance of  :class:`Litestar <.app.Litestar>`
2. An object named ``application`` that's an instance of  :class:`Litestar <.app.Litestar>`
3. Any object that's an instance of :class:`Litestar <.app.Litestar>`
4. A callable named ``create_app``
5. A callable that's annotated as returning an instance of :class:`Litestar <.app.Litestar>`


Commands
--------

litestar
^^^^^^^^

The ``litestar`` command is the main entrypoint to the CLI. If the ``--app`` flag is not passed,
the app will be automatically discovered as described in `the section above <autodiscovery>`_

Options
~~~~~~~

+---------------+---------------------------+-----------------------------------------------------------------+
| Flag          | Environment variable      | Description                                                     |
+===============+===========================+=================================================================+
| ``--app``     | ``LITESTAR_APP``          | ``<modulename>.<submodule>:<app instance>``                     |
+---------------+---------------------------+-----------------------------------------------------------------+
| ``--app-dir`` | N/A                       | Look for APP in the specified directory, by adding this to the  |
|               |                           | PYTHONPATH. Defaults to the current working directory.          |
+---------------+---------------------------+-----------------------------------------------------------------+

version
^^^^^^^

Print the currently installed version of Litestar

Options
~~~~~~~

+-------------------------+------------------------------------+
| Name                    | Description                        |
+=========================+====================================+
| ``-s``\ , ``--short``   | Include only ``MAJOR.MINOR.PATCH`` |
+-------------------------+------------------------------------+


Run
^^^

The ``run`` command runs a Litestar application using `uvicorn <https://www.uvicorn.org/>`_.

.. code-block:: shell

   litestar run

.. caution::

    This feature is intended for development purposes only and should not be used to
    deploy production applications

.. _cli-run-options:

Options
~~~~~~~

+-------------------------------------+---------------------------+-----------------------------------------------------------------+
| Flag                                | Environment variable      | Description                                                     |
+========================+============+=========+=================+=================================================================+
| ``-r``\ , ``--reload``              | ``LITESTAR_RELOAD``       |  Reload the application when files in its directory are changed |
+-------------------------------------+---------------------------+-----------------------------------------------------------------+
| ``-p``\ , ``--port``                | ``LITESTAR_PORT``         | Bind the the server to this port [default: 8000]                |
+-------------------------------------+---------------------------+-----------------------------------------------------------------+
| ``-wc``\ , ``--web-concurrency``    | ``WEB_CONCURRENCY``       | The number of concurrent web workers to start [default: 1]      |
+-------------------------------------+---------------------------+-----------------------------------------------------------------+
| ``--host``                          | ``LITESTAR_HOST``         | Bind the server to this host [default: 127.0.0.1]               |
+-------------------------------------+---------------------------+-----------------------------------------------------------------+
| ``--debug``                         | ``LITESTAR_DEBUG``        | Run the application in debug mode                               |
+-------------------------------------+---------------------------+-----------------------------------------------------------------+


info
^^^^

The ``info`` command displays useful information about the selected application and its configuration

.. code-block:: shell

   litestar info


.. image:: /images/cli/litestar_info.png
   :alt: litestar info


routes
^^^^^^

The ``routes`` command displays a tree view of the routing table

.. code-block:: shell

   litestar routes


.. image:: /images/cli/litestar_routes.png
   :alt: litestar info


sessions
^^^^^^^^

This command and its subcommands provide management utilities for
:ref:`server-side session backends <usage/middleware/builtin-middleware:server-side sessions>`.

delete
~~~~~~

The ``delete`` subcommand deletes a specific session from the backend.

.. code-block:: shell

   litestar sessions delete cc3debc7-1ab6-4dc8-a220-91934a473717

clear
~~~~~

The ``clear`` subcommand clears all sessions from the backend.

.. code-block:: shell

   litestar sessions clear

OpenAPI
^^^^^^^

This command provides utilities to generate OpenAPI schema and TypeScript types.

schema
~~~~~~

The ``schema`` subcommand generates OpenAPI specs from the Litestar application, serializing these as either JSON or YAML.
The serialization format depends on the filename, which is by default ``openapi_schema.json``. You can specify a different
filename using the ``--output`` flag. For example:

.. code-block:: shell

   litestar openapi schema --output my-specs.yaml

typescript
~~~~~~~~~~

The ``typescript`` subcommand generates TypeScript definitions from the Litestar application's OpenAPI specs.  For example:

.. code-block:: shell

   litestar openapi typescript

By default, this command will output a file called ``api-specs.ts``. You can change this using the ``--output`` option:

.. code-block:: shell

   litestar openapi typescript --output my-types.ts

You can also specify the top level TypeScript namespace that will be created, which by default will be called API:

.. code-block:: typescript

   export namespace API {
       // ...
   }

To do this use the ``--namespace`` option:

.. code-block:: shell

   litestar openapi typescript --namespace MyNamespace

Which will result in:

.. code-block:: typescript

   export namespace MyNamespace {
       // ...
   }

Extending the CLI
-----------------

Litestar's CLI is built with `click <https://click.palletsprojects.com/>`_, and can be easily extended.
All that's needed to add subcommands under the ``litestar`` command is adding an
`entry point <https://packaging.python.org/en/latest/specifications/entry-points/>`_, pointing to a
:class:`click.Command` or :class:`click.Group`, under the
``litestar.commands`` group.

.. tab-set::

    .. tab-item:: setup.py

        .. code-block:: python

           from setuptools import setup

           setup(
               name="my-litestar-plugin",
               ...,
               entry_points={
                   "litestar.commands": ["my_command=my_litestar_plugin.cli:main"],
               },
           )



    .. tab-item:: poetry

        .. code-block:: toml

           [tool.poetry.plugins."litestar.commands"]
           my_command = "my_litestar_plugin.cli:main"



Accessing the app instance
^^^^^^^^^^^^^^^^^^^^^^^^^^

When extending the Litestar CLI, you most likely need access to the loaded ``Litestar`` instance.
This can be achieved by adding the special ``app`` parameter to your CLI functions. This will cause
``Litestar`` instance to be injected into the function whenever it is being called from a click-context.

.. code-block:: python

   import click
   from litestar import Litestar


   @click.command()
   def my_command(app: Litestar) -> None:
       ...
