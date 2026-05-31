Docker
======

Docker 是一个容器化平台，允许您将应用程序及其所有依赖项打包在一起。它对于为应用程序创建一致的运行环境非常有用，无论主机系统及其自身的配置或依赖项如何 - 这在防止依赖冲突方面特别有帮助。

本指南使用 `Docker 官方 Python 容器 <https://hub.docker.com/_/python>`_ 作为基础镜像。

何时使用
--------

Docker 非常适合在以下场景中部署 Python Web 应用程序：

- **隔离：** 您需要为应用程序提供一致的隔离环境，独立于主机系统。
- **可扩展性：** 您的应用程序需要根据需求轻松扩展或缩减。
- **可移植性：** 需要在不同环境（开发、测试、生产）中一致地运行应用程序至关重要。
- **微服务架构：** 您正在采用微服务架构，其中每个服务都可以独立容器化和管理。
- **持续集成/持续部署 (CI/CD)：** 您正在实施 CI/CD 管道，Docker 有助于应用程序的构建、测试和部署。
- **依赖管理：** 确保您的应用程序将其所有依赖项捆绑在一起，而不会与其他应用程序发生冲突。

替代方案
~~~~~~~~~~~~

对于不同的部署场景，请考虑以下替代方案：

- `systemd <https://www.freedesktop.org/wiki/Software/systemd/>`_：
    一个系统和服务管理器，集成到许多 Linux 发行版中以管理系统进程。

    .. note:: 官方文档即将推出
- :doc:`Supervisor <supervisor>`：
    一个进程控制系统，可用于自动启动、停止和重启进程；包括 Web UI。
- :doc:`手动使用 ASGI 服务器 <manually-with-asgi-server>`：
    通过使用 ASGI 服务器（如 Uvicorn、Hypercorn、Daphne 等）运行应用程序来直接控制。

本指南假设您已在系统上安装并运行 Docker，并且项目目录中有以下文件：

.. code-block:: shell
    :caption: ``requirements.txt``

    litestar[standard]>=2.4.0,<3.0.0

.. code-block:: python
    :caption: ``app.py``

    """最小的 Litestar 应用程序。"""

    from asyncio import sleep
    from typing import Any, Dict

    from litestar import Litestar, get


    @get("/")
    async def async_hello_world() -> Dict[str, Any]:
        """输出 hello world 的路由处理程序。"""
        await sleep(0.1)
        return {"hello": "world"}


    @get("/sync", sync_to_thread=False)
    def sync_hello_world() -> Dict[str, Any]:
        """输出 hello world 的路由处理程序。"""
        return {"hello": "world"}


    app = Litestar(route_handlers=[sync_hello_world, async_hello_world])

Dockerfile
----------

.. code-block:: docker
    :caption: 示例 Dockerfile

    # 使用 Python 3.12 和 Debian Bookworm 设置基础镜像
    FROM python:3.12-slim-bookworm

    # 将工作目录设置为 /app
    WORKDIR /app

    # 仅将必要的文件复制到工作目录
    COPY . /app

    # 安装依赖项
    RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

    # 暴露应用程序运行的端口
    EXPOSE 80

    # 使用 Litestar CLI 运行应用程序
    CMD ["litestar", "run", "--host", "0.0.0.0", "--port", "80"]

这会将您的本地项目文件夹复制到 Docker 容器中的 ``/app`` 目录，并通过 ``uvicorn`` 使用 ``litestar run`` 命令运行您的应用程序。``uvicorn`` 由 ``litestar[standard]`` 附加组件提供，该组件在 ``requirements.txt`` 文件中安装。

如果您愿意，也可以直接使用 :doc:`ASGI 服务器 <manually-with-asgi-server>` 启动应用程序。

定义 ``Dockerfile`` 后，您可以使用 ``docker build`` 构建镜像，并使用 ``docker run`` 运行它。

.. dropdown:: 有用的 Dockerfile 命令

    .. code-block:: shell
        :caption: 有用的 Docker 命令

        # 构建容器
        docker build -t exampleapp .

        # 运行容器
        docker run -d -p 80:80 --name exampleapp exampleapp

        # 停止容器
        docker stop exampleapp

        # 启动容器
        docker start exampleapp

        # 删除容器
        docker rm exampleapp

Docker Compose
--------------

Compose 是一个用于定义和运行多容器 Docker 应用程序的工具。
在 `官方 Docker 文档 <https://docs.docker.com/compose/>`_ 中了解有关 Compose 的更多信息。

如果您想将容器作为 Docker Compose 设置的一部分运行，则可以简单地使用此 compose 文件：

.. code-block:: yaml
    :caption: ``docker-compose.yml``

    version: "3.9"

    services:
      exampleapp:
        build:
          context: ./
          dockerfile: Dockerfile
        container_name: "exampleapp"
        depends_on:
          - database
        ports:
          - "80:80"
        environment:
          - DB_HOST=database
          - DB_PORT=5432
          - DB_USER=litestar
          - DB_PASS=r0cks
          - DB_NAME=exampleapp

      database:
        image: postgres:latest
        container_name: "exampledb"
        environment:
          POSTGRES_USER: exampleuser
          POSTGRES_PASSWORD: examplepass
          POSTGRES_DB: exampledb
        ports:
          - "5432:5432"
        volumes:
          - db_data:/var/lib/postgresql/data

    volumes:
      db_data:

此 compose 文件定义了两个服务：``exampleapp`` 和 ``database``。``exampleapp`` 服务从当前目录中的 Dockerfile 构建，并暴露端口 80。``database`` 服务使用官方 PostgreSQL 镜像，并暴露端口 ``5432``。``exampleapp`` 服务依赖于 ``database`` 服务，因此数据库将在应用程序之前启动。``exampleapp`` 服务还为数据库连接详细信息设置了环境变量，应用程序使用这些变量。

定义 ``docker-compose.yml`` 后，您可以运行 ``docker compose up`` 来启动容器。您还可以运行 ``docker compose up -d`` 以在后台或"分离"模式下运行容器。

.. dropdown:: 有用的 Compose 命令

    .. code-block:: shell
        :caption: 有用的 Docker Compose 命令

        # 构建容器
        docker compose build

        # 运行容器
        docker compose up

        # 在后台运行容器
        docker compose up -d

        # 停止容器
        docker compose down
