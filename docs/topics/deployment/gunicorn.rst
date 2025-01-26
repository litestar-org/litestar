Gunicorn with Uvicorn workers
=============================

Gunicorn (Green Unicorn) is a Python WSGI HTTP Server that can be used with uvicorn workers to deploy ASGI applications.

Use When
--------

Gunicorn with Uvicorn workers is commonly used in scenarios where you need:

- **Process Management**: When you need a robust process manager to handle multiple worker processes, automatic worker restarts, and graceful reloads.
- **Load Distribution**: When your application needs to utilize multiple CPU cores by running multiple worker processes to handle concurrent requests.
- **Production Deployments**: When deploying applications that require process monitoring, health checks, and automatic recovery from failures.
- **Resource Control**: When you need fine-grained control over worker lifecycle, timeouts, and resource limits.
- **Zero-downtime Deployments**: When you need to perform rolling restarts of worker processes without dropping requests.

These features make it particularly suitable for production environments where reliability and process management are critical requirements.

.. important:: **Deprecation Notice**

    The Gunicorn+Uvicorn pattern is considered legacy for ASGI deployments since `Uvicorn 0.30.0+ <https://github.com/encode/uvicorn/releases/tag/0.30.0/>`_ includes native worker management. 

    - Uvicorn added a new multiprocess manager, that is meant to replace Gunicorn entirely.
    - The main goal is to be able to have a proper process manager that can handle multiple workers and restart them when needed.
    - You can see more details on the the pull request `#2183 <https://github.com/encode/uvicorn/pull/2183/>`_.

    For new deployments, use Uvicorn directly:

    .. code-block:: shell

        uvicorn app:app --workers 4

Alternatives
~~~~~~~~~~~~

For different deployment scenarios, consider these alternatives:

- :doc:`NGINX Unit <nginx-unit>`:
    A dynamic web and application server, suitable for running and managing multiple applications.
- `systemd <https://www.freedesktop.org/wiki/Software/systemd/>`_:
    A system and service manager, integrated into many Linux distributions for managing system processes.

    .. note:: Official documentation coming soon
- :doc:`Manually with an ASGI server <manually-with-asgi-server>`:
    Direct control by running the application with an ASGI server like Uvicorn, Hypercorn, Daphne, etc.
- `systemd <https://www.freedesktop.org/wiki/Software/systemd/>`_:
    A system and service manager, integrated into many Linux distributions for managing system processes.

    .. note:: Official documentation coming soon
- :doc:`Supervisor <supervisor>`:
    A process control system that can be used to automatically start, stop and restart processes; includes a web UI.
- :doc:`Docker <docker>`:
    Ideal for containerized environments, offering isolation and scalability.

Installation
------------

.. code-block:: shell

    pip install gunicorn uvicorn

Create a ``app.py`` file containing the reference of your Litestar app

.. literalinclude:: /examples/todo_app/hello_world.py
    :language: python
    :caption: app.py

Command Line Usage
------------------

Basic startup command:

.. tab-set::

    .. tab-item:: Basic

        .. code-block:: shell
            :caption: Start with 4 worker processes

            gunicorn app:app -w 4 -k uvicorn.workers.UvicornWorker

    .. tab-item:: With Environment Variables

        .. code-block:: shell
            :caption: Production-ready configuration with Docker

            gunicorn app:app \
                --bind 127.0.0.1:8000 \
                --worker-class uvicorn.workers.UvicornWorker \
                --workers ${WORKERS_PER_CORE:-4} \
                --max-workers ${MAX_WORKERS:-8} \
                --timeout 120 \
                --keep-alive 5

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

Integration with Project Code
-----------------------------

Create a management script in your project (e.g. ``gunicorn_runner.py``):

.. tab-set::

    .. tab-item:: subprocess

        .. code-block:: python
            :caption: gunicorn_runner.py

            import subprocess
            import sys
            import os


            def main() -> None:
                proc = subprocess.Popen(
                    [
                        sys.executable,
                        "-m",
                        "gunicorn",
                        "app:app",
                        "--workers",
                        os.environ.get("WORKERS", "1"),
                        "--bind",
                        f"{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('PORT', '8000')}",
                        "--worker-class",
                        "uvicorn.workers.UvicornWorker",
                    ]
                )

                try:
                    proc.wait()
                
                except KeyboardInterrupt:
                    proc.terminate()
                    proc.wait(timeout=5)


            if __name__ == "__main__":
                main()

    .. tab-item:: BaseApplication

        For advanced usage, you can use the ``BaseApplication`` class directly. It will allow us to override Gunicorn's own logging configuration.

        .. code-block:: python
            :caption: gunicorn_runner.py

            from __future__ import annotations

            import os
            from typing import TYPE_CHECKING

            from gunicorn.app.base import BaseApplication

            from app import app
            
            if TYPE_CHECKING:
                from litestar import Litestar


            class StandaloneApplication(BaseApplication):
                """Our Gunicorn application."""

                def __init__(self, app: Litestar, options: dict[str, str] | None = None):
                    self.options = options or {}
                    self.application = app
                    super().__init__()

                def load_config(self):
                    if self.cfg is None:
                        raise AssertionError("StandaloneApplication must be loaded by a parent class")

                    config = {key: value for key, value in self.options.items() if key in self.cfg.settings and value is not None}
                    for key, value in config.items():
                        self.cfg.set(key.lower(), value)

                def load(self):
                    return self.application


            if __name__ == "__main__":
                options = {
                    "bind": f"{os.environ.get('HOST', '127.0.0.1')}:{os.environ.get('PORT', '8000')}",
                    "workers": int(os.environ.get("WORKERS", "1")),
                    "worker_class": "uvicorn.workers.UvicornWorker",
                }
                StandaloneApplication(app, options).run()
