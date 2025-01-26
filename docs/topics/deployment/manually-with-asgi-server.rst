Manually with ASGI server
=========================

ASGI (Asynchronous Server Gateway Interface) is intended to provide a standard interface between async Python web
frameworks like Litestar, and async web servers.

There are several popular ASGI servers available, and you can choose the one that best fits your application's needs.

Use When
--------

Running your application manually with an ASGI server is usually only ideal in development and testing environments.

It is generally recommended to run your production workloads inside a containerized environment, such as
:doc:`Docker <docker>` or Kubernetes or via a process control system
such as :doc:`Supervisor <supervisor>` or ``systemd``.

Alternatives
~~~~~~~~~~~~

For different deployment scenarios, consider these alternatives:

- :doc:`NGINX Unit <nginx-unit>`:
    A dynamic web and application server, suitable for running and managing multiple applications.
- `systemd <https://www.freedesktop.org/wiki/Software/systemd/>`_:
    A system and service manager, integrated into many Linux distributions for managing system processes.

    .. note:: Official documentation coming soon
- :doc:`Supervisor <supervisor>`:
    A process control system that can be used to automatically start, stop and restart processes; includes a web UI.
- :doc:`Docker <docker>`:
    Ideal for containerized environments, offering isolation and scalability.

Choosing an ASGI Server
-----------------------

.. tab-set::

    .. tab-item:: Uvicorn
        :sync: uvicorn

        `Uvicorn <https://www.uvicorn.org/>`_ is an ASGI server that supports ``HTTP/1.1`` and WebSocket.

    .. tab-item:: Hypercorn
        :sync: hypercorn

        `Hypercorn <https://hypercorn.readthedocs.io/en/latest/#/>`_ is an ASGI server that was initially part of
        `Quart <https://pgjones.gitlab.io/quart//>`_, and supports ``HTTP/1.1``, ``HTTP/2``, and WebSocket.

    .. tab-item:: Daphne
        :sync: daphne

        `Daphne <https://github.com/django/daphne/>`_ is an ASGI server that was originally developed for
        `Django Channels <https://channels.readthedocs.io/en/latest/>`_, and supports ``HTTP/1.1``, ``HTTP/2``, and
        WebSocket.

    .. tab-item:: Granian
        :sync: granian

        `Granian <https://github.com/emmett-framework/granian/>`_ is a Rust-based ASGI server that supports ``HTTP/1.1``,
        ``HTTP/2``, and WebSocket.

Install the ASGI Server
-----------------------

.. tab-set::

    .. tab-item:: Uvicorn
        :sync: uvicorn

        .. code-block:: shell
            :caption: Install Uvicorn with pip

            pip install uvicorn

    .. tab-item:: Hypercorn
        :sync: hypercorn

        .. code-block:: shell
            :caption: Install Hypercorn with pip

            pip install hypercorn

    .. tab-item:: Daphne
        :sync: daphne

        .. code-block:: shell
            :caption: Install Daphne with pip

            pip install daphne

    .. tab-item:: Granian
        :sync: granian

        .. code-block:: shell
            :caption: Install Granian with pip

            pip install granian

Run the ASGI Server
-------------------

Assuming your app is defined in the same manner as :ref:`Minimal Example <minimal_example>`, you can run the
ASGI server with the following command:

.. tab-set::

    .. tab-item:: Uvicorn
        :sync: uvicorn

        .. code-block:: shell
            :caption: Run Uvicorn with the default configuration

            uvicorn app:app

        .. code-block:: console
            :caption: Console Output

            INFO:     Waiting for application startup.
            INFO:     Application startup complete.
            INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)

    .. tab-item:: Hypercorn
        :sync: hypercorn

        .. code-block:: shell
            :caption: Run Hypercorn with the default configuration

            hypercorn app:app

        .. code-block:: console
            :caption: Console Output

            [2023-11-12 23:31:26 -0800] [16748] [INFO] Running on http://127.0.0.1:8000 (CTRL + C to quit)

    .. tab-item:: Daphne
        :sync: daphne

        .. code-block:: shell
            :caption: Run Daphne with the default configuration

            daphne app:app

        .. code-block:: console
            :caption: Console Output

            INFO - 2023-11-12 23:31:51,571 - daphne.cli - cli - Starting server at tcp:port=8000:interface=127.0.0.1
            INFO - 2023-11-12 23:31:51,572 - daphne.server - server - Listening on TCP address 127.0.0.1:8000

    .. tab-item:: Granian
        :sync: granian

        .. code-block:: shell
            :caption: Run Granian with the default configuration

            granian --interface asgi app:app

        .. code-block:: console
            :caption: Console Output

            [INFO] Starting granian
            [INFO] Listening at: 127.0.0.1:8000

Gunicorn with Uvicorn workers
-----------------------------

.. important:: **Deprecation Notice**

    The Gunicorn+Uvicorn pattern is considered legacy for ASGI deployments since `Uvicorn 0.30.0+ <https://github.com/encode/uvicorn/releases/tag/0.30.0/>`_ includes native worker management.

    Uvicorn added a new multiprocess manager, that is meant to replace Gunicorn entirely. Refer to the pull request `#2183 <https://github.com/encode/uvicorn/pull/2183/>`_ for implementation details.

    For new deployments, use `Uvicorn <#run-the-asgi-server>`_ directly.

Gunicorn (Green Unicorn) is WSGI server which can serve applications like Flask and Django. Gunicorn by itself is not compatible with Litestar, as Litestar uses the newest ASGI standard.

But Gunicorn supports working as a process manager and allowing users to tell it which specific worker process class to use. Then Gunicorn would start one or more worker processes using that class. And Uvicorn has a Gunicorn-compatible worker class, so you can use Uvicorn workers with Gunicorn to deploy ASGI applications.

.. code-block:: shell
    :caption: Start with 4 worker processes

    gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker

.. code-block:: console
    :caption: Console Output

    [2025-01-24 23:51:22 +0800] [35955] [INFO] Starting gunicorn 23.0.0
    [2025-01-24 23:51:22 +0800] [35955] [INFO] Listening at: http://127.0.0.1:8000 (35955)
    [2025-01-24 23:51:22 +0800] [35955] [INFO] Using worker: uvicorn.workers.UvicornWorker
    [2025-01-24 23:51:22 +0800] [35962] [INFO] Booting worker with pid: 35962
    [2025-01-24 23:51:22 +0800] [35963] [INFO] Booting worker with pid: 35963
    [2025-01-24 23:51:22 +0800] [35964] [INFO] Booting worker with pid: 35964
    [2025-01-24 23:51:22 +0800] [35965] [INFO] Booting worker with pid: 35965
    [2025-01-24 23:51:23 +0800] [35962] [INFO] Started server process [35962]
    [2025-01-24 23:51:23 +0800] [35962] [INFO] Waiting for application startup.
    [2025-01-24 23:51:23 +0800] [35962] [INFO] Application startup complete.
    [2025-01-24 23:51:23 +0800] [35963] [INFO] Started server process [35963]
    [2025-01-24 23:51:23 +0800] [35963] [INFO] Waiting for application startup.
    [2025-01-24 23:51:23 +0800] [35963] [INFO] Application startup complete.
    [2025-01-24 23:51:23 +0800] [35964] [INFO] Started server process [35964]
    [2025-01-24 23:51:23 +0800] [35964] [INFO] Waiting for application startup.
    [2025-01-24 23:51:23 +0800] [35964] [INFO] Application startup complete.
    [2025-01-24 23:51:23 +0800] [35965] [INFO] Started server process [35965]
    [2025-01-24 23:51:23 +0800] [35965] [INFO] Waiting for application startup.
    [2025-01-24 23:51:23 +0800] [35965] [INFO] Application startup complete.
