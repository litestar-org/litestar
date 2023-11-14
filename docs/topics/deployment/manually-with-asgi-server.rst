Manually with ASGI server
==========

ASGI (Asynchronous Server Gateway Interface) is intended to provide a standard interface between async Python web frameworks like Litestar, and async web servers. There are several popular ASGI servers available, and you can choose the one that best fits your application's needs.

Choosing an ASGI Server
-----------------------
.. tab-set::

    .. tab-item:: Uvicorn
        :sync: uvicorn

        `Uvicorn <https://www.uvicorn.org/>`_ is an ASGI server that supports HTTP/1.1 and WebSocket.

    .. tab-item:: Hypercorn
        :sync: hypercorn

        `Hypercorn <https://hypercorn.readthedocs.io/en/latest/#/>`_ is an ASGI server that was initially part of `Quart <https://pgjones.gitlab.io/quart//>`_, and supports HTTP/1.1, HTTP/2, and WebSocket.

    .. tab-item:: Daphne
        :sync: daphne

        `Daphne <https://github.com/django/daphne/>`_ is an ASGI server that was originally developed for `Django Channels <https://channels.readthedocs.io/en/latest/>`_, and supports HTTP/1.1, HTTP/2, and WebSocket.

    .. tab-item:: Granian
        :sync: granian

        `Granian <https://github.com/emmett-framework/granian/>`_ is a Rust based ASGI server that supports HTTP/1.1, HTTP/2, and WebSocket.

Install the ASGI Server
-----------------------
.. tab-set::

    .. tab-item:: Uvicorn
        :sync: uvicorn

        .. code-block:: shell

            pip install uvicorn

    .. tab-item:: Hypercorn
        :sync: hypercorn

        .. code-block:: shell

            pip install hypercorn

    .. tab-item:: Daphne
        :sync: daphne

        .. code-block:: shell

            pip install daphne

    .. tab-item:: Granian
        :sync: granian

        .. code-block:: shell

            pip install granian

Run the ASGI Server
-------------------
Assuming your app defined in the same manner as :ref:`Minimal Example <minimal_example>`, you can run the ASGI server with the following command:

.. tab-set::

    .. tab-item:: Uvicorn
        :sync: uvicorn

        .. code-block:: shell

            uvicorn app:app

        .. code-block:: none

            INFO:     Waiting for application startup.
            INFO:     Application startup complete.
            INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)

    .. tab-item:: Hypercorn
        :sync: hypercorn

        .. code-block:: shell

            hypercorn app:app

        .. code-block:: none

            [2023-11-12 23:31:26 -0800] [16748] [INFO] Running on http://127.0.0.1:8000 (CTRL + C to quit)

    .. tab-item:: Daphne
        :sync: daphne

        .. code-block:: shell

            daphne app:app

        .. code-block:: none

            INFO - 2023-11-12 23:31:51,571 - daphne.cli - cli - Starting server at tcp:port=8000:interface=127.0.0.1
            INFO - 2023-11-12 23:31:51,572 - daphne.server - server - Listening on TCP address 127.0.0.1:8000

    .. tab-item:: Granian
        :sync: granian

        .. code-block:: shell

            granian --interface asgi app:app

        .. code-block:: none

            [INFO] Starting granian
            [INFO] Listening at: 127.0.0.1:8000
