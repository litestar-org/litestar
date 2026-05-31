使用 ASGI 服务器手动部署
=========================

ASGI（异步服务器网关接口）旨在为像 Litestar 这样的异步 Python Web 框架和异步 Web 服务器之间提供标准接口。

有几个流行的 ASGI 服务器可用，您可以选择最适合您应用程序需求的服务器。

何时使用
--------

使用 ASGI 服务器手动运行应用程序通常仅适用于开发和测试环境。

通常建议在容器化环境中运行生产工作负载，例如 :doc:`Docker <docker>` 或 Kubernetes，或通过进程控制系统，例如 :doc:`Supervisor <supervisor>` 或 ``systemd``。

替代方案
~~~~~~~~~~~~

对于不同的部署场景，请考虑以下替代方案：

- `systemd <https://www.freedesktop.org/wiki/Software/systemd/>`_：
    一个系统和服务管理器，集成到许多 Linux 发行版中以管理系统进程。

    .. note:: 官方文档即将推出
- :doc:`Supervisor <supervisor>`：
    一个进程控制系统，可用于自动启动、停止和重启进程；包括 Web UI。
- :doc:`Docker <docker>`：
    适用于容器化环境，提供隔离和可扩展性。

选择 ASGI 服务器
-----------------------

.. tab-set::

    .. tab-item:: Uvicorn
        :sync: uvicorn

        `Uvicorn <https://www.uvicorn.org/>`_ 是一个支持 ``HTTP/1.1`` 和 WebSocket 的 ASGI 服务器。

    .. tab-item:: Hypercorn
        :sync: hypercorn

        `Hypercorn <https://hypercorn.readthedocs.io/en/latest/#/>`_ 是一个 ASGI 服务器，最初是 `Quart <https://pgjones.gitlab.io/quart//>`_ 的一部分，支持 ``HTTP/1.1``、``HTTP/2`` 和 WebSocket。

    .. tab-item:: Daphne
        :sync: daphne

        `Daphne <https://github.com/django/daphne/>`_ 是一个 ASGI 服务器，最初是为 `Django Channels <https://channels.readthedocs.io/en/latest/>`_ 开发的，支持 ``HTTP/1.1``、``HTTP/2`` 和 WebSocket。

    .. tab-item:: Granian
        :sync: granian

        `Granian <https://github.com/emmett-framework/granian/>`_ 是一个基于 Rust 的 ASGI 服务器，支持 ``HTTP/1.1``、``HTTP/2`` 和 WebSocket。

安装 ASGI 服务器
-----------------------

.. tab-set::

    .. tab-item:: Uvicorn
        :sync: uvicorn

        .. code-block:: shell
            :caption: 使用 pip 安装 Uvicorn

            pip install uvicorn

    .. tab-item:: Hypercorn
        :sync: hypercorn

        .. code-block:: shell
            :caption: 使用 pip 安装 Hypercorn

            pip install hypercorn

    .. tab-item:: Daphne
        :sync: daphne

        .. code-block:: shell
            :caption: 使用 pip 安装 Daphne

            pip install daphne

    .. tab-item:: Granian
        :sync: granian

        .. code-block:: shell
            :caption: 使用 pip 安装 Granian

            pip install granian

运行 ASGI 服务器
-------------------

假设您的应用程序的定义方式与 :ref:`最小示例 <minimal_example>` 相同，您可以使用以下命令运行 ASGI 服务器：

.. tab-set::

    .. tab-item:: Uvicorn
        :sync: uvicorn

        .. code-block:: shell
            :caption: 使用默认配置运行 Uvicorn

            uvicorn app:app

        .. code-block:: console
            :caption: 控制台输出

            INFO:     Waiting for application startup.
            INFO:     Application startup complete.
            INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)

    .. tab-item:: Hypercorn
        :sync: hypercorn

        .. code-block:: shell
            :caption: 使用默认配置运行 Hypercorn

            hypercorn app:app

        .. code-block:: console
            :caption: 控制台输出

            [2023-11-12 23:31:26 -0800] [16748] [INFO] Running on http://127.0.0.1:8000 (CTRL + C to quit)

    .. tab-item:: Daphne
        :sync: daphne

        .. code-block:: shell
            :caption: 使用默认配置运行 Daphne

            daphne app:app

        .. code-block:: console
            :caption: 控制台输出

            INFO - 2023-11-12 23:31:51,571 - daphne.cli - cli - Starting server at tcp:port=8000:interface=127.0.0.1
            INFO - 2023-11-12 23:31:51,572 - daphne.server - server - Listening on TCP address 127.0.0.1:8000

    .. tab-item:: Granian
        :sync: granian

        .. code-block:: shell
            :caption: 使用默认配置运行 Granian

            granian --interface asgi app:app

        .. code-block:: console
            :caption: 控制台输出

            [INFO] Starting granian
            [INFO] Listening at: 127.0.0.1:8000

Gunicorn 与 Uvicorn workers
-----------------------------

.. important:: **弃用通知**

    自 `Uvicorn 0.30.0+ <https://github.com/encode/uvicorn/releases/tag/0.30.0/>`_ 包含原生 worker 管理以来，Gunicorn+Uvicorn 模式被视为 ASGI 部署的遗留模式。

    Uvicorn 添加了一个新的多进程管理器，旨在完全替代 Gunicorn。有关实现细节，请参阅拉取请求 `#2183 <https://github.com/encode/uvicorn/pull/2183/>`_。

    对于新部署，请直接使用 Uvicorn。
