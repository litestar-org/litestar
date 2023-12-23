NGINX Unit
==========

``nginx-unit`` is a dynamic web application server, designed to run applications in multiple languages,
serve static files, and more.

Use When
--------

Running your application with ``nginx-unit`` is preferable when you need to run your application in a production
environment, with a high level of control over the process.

For detailed understanding and further information, refer to the official
`nginx-unit documentation <https://unit.nginx.org/>`_.

Alternatives
++++++++++++

- :doc:`Manually with an ASGI server <manually-with-asgi-server>`:
    Direct control by running the application with an ASGI server like Uvicorn, Hypercorn, Daphne, etc.
- `systemd <https://www.freedesktop.org/wiki/Software/systemd/>`_:
    A system and service manager, integrated into many Linux distributions for managing system processes.

    .. note:: Official documentation coming soon
- :doc:`Supervisor <supervisor>`:
    A process control system that can be used to automatically start, stop and restart processes; includes a web UI.
- :doc:`Docker <docker>`:
    Ideal for containerized environments, offering isolation and scalability.

    .. note:: You can deploy ``nginx-unit`` with Docker using the
        `official NGINX image <https://unit.nginx.org/howto/docker/>`_.

Install ``nginx-unit``
----------------------

To install ``nginx-unit``, refer to the `official documentation <https://unit.nginx.org/installation/>`_

.. tab-set::

   .. tab-item:: macOS (`Brew <https://brew.sh/>`_)

        .. literalinclude:: /examples/deployment/nginx-unit/install-macos.sh
            :language: sh

   .. tab-item:: Ubuntu

        To be done


Start the process, replace ``user`` by your system user.

.. code-block:: sh
    :caption: Start nginx-unit

    unitd --user <user>


3. Create a ``run.py`` file containing the reference of your Litestar app

.. literalinclude:: /examples/todo_app/hello_world.py
    :language: python
    :caption: run.py

Configuration
-------------

Create a file called ``unit.json``, put it at the root of the your project

.. literalinclude:: /examples/deployment/nginx-unit/unit.json
    :language: json
    :caption: unit.json

Listeners
+++++++++

To accept requests, add a listener object in the ``config/listeners`` API section; the object’s name can be:

- A unique IP socket: ``127.0.0.1:80``, ``[::1]:8080``
- A wildcard that matches any host IPs on the port: ``*:80``
- On Linux-based systems, abstract UNIX sockets can be used as well: ``unix:@abstract_socket``.


Applications
++++++++++++

Each app that Unit runs is defined as an object in the ``/config/applications`` section of the control API;
it lists the app’s language and settings, runtime limits, process model, and various language-specific options.

+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| Option                 | Value                 | Description                                                                                                                                            |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``type`` (required)    | ``python 3.12``       | Application type: ``python`` ``"type": "python 3"``, ``"type": "python 3.12"``                                                                         |
|                        |                       |                                                                                                                                                        |
|                        |                       | Unit searches its modules and uses the latest matching one, reporting an error if none match.                                                          |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``home``               | ``venv``              | String; path to the app’s virtual environment. Absolute or relative to ``working_directory``.                                                          |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``path``               | ``src/app``           | String or an array of strings; additional Python module lookup paths. These values are prepended to ``sys.path``.                                      |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``module`` (required)  | ``run``               | String; app’s module name. This module is imported by Unit the usual Python way.                                                                       |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``callable``           | ``app``               | String; name of the module-based callable that Unit runs as the app. The default is `application`.                                                     |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``working_directory``  | ``<path_to_project>`` | String; the app’s working directory. The default is the working directory of Unit’s main process.                                                      |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``stderr``, ``stdout`` | ``log_error.log``     | Strings; filenames where Unit redirects the application’s output.                                                                                      |
|                        |                       |                                                                                                                                                        |
|                        |                       | The default is ``/dev/null``.                                                                                                                          |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``user``               |                       | String; username that runs the app process.                                                                                                            |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``group``              |                       | String; group name that runs the app process. The default is the ``user``’s primary group.                                                             |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+
| ``processes``          | ``1``                 | Integer or object; integer sets a static number of app processes, and object options `max`, `spare`, and `idle_timeout` enable dynamic management.     |
|                        |                       |                                                                                                                                                        |
|                        |                       | The default is ``1``.                                                                                                                                  |
+------------------------+-----------------------+--------------------------------------------------------------------------------------------------------------------------------------------------------+

Configuration update
--------------------

To update the ``nginx-unit`` service already running, use ``PUT`` method to send the ``unit.json`` file on the
``/config`` endpoint

.. code-block:: sh
    :caption: Update nginx-unit configuration

    curl -X PUT --data-binary @unit.json --unix-socket /opt/homebrew/var/run/unit/control.sock http://localhost/config
