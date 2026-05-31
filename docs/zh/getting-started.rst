===============
入门指南
===============

安装
----

.. code-block:: shell

   pip install litestar

.. tip:: ``litestar[standard]`` 包含常用的扩展，例如 CLI、``uvicorn`` 与 ``jinja2``（用于模板）。

.. dropdown:: 可选扩展
    :icon: star

    `Pydantic <https://docs.pydantic.dev/latest/>`_
        :code:`pip install 'litestar[pydantic]'`

    `Attrs <https://www.attrs.org>`_
        :code:`pip install 'litestar[attrs]'`

    :ref:`Brotli Compression Middleware <usage/middleware/builtin-middleware:brotli>`
        :code:`pip install 'litestar[brotli]'`

   :ref:`Zstd Compression Middleware <usage/middleware/builtin-middleware:zstd>`
        :code:`pip install 'litestar[zstd]'`

    :ref:`Cookie Based Sessions <usage/middleware/builtin-middleware:client-side sessions>`
        :code:`pip install 'litestar[cryptography]'`

    :doc:`JWT </usage/security/jwt>`
        :code:`pip install 'litestar[jwt]'`

    :doc:`RedisStore </usage/stores>`
        :code:`pip install 'litestar[redis]'`

    :ref:`Picologging <usage/logging:using picologging>`
        :code:`pip install 'litestar[picologging]'`

    :ref:`StructLog <usage/logging:using structlog>`
        :code:`pip install 'litestar[structlog]'`

    :doc:`Prometheus Instrumentation </usage/metrics/prometheus>`
        :code:`pip install 'litestar[prometheus]'`

    :doc:`Open Telemetry Instrumentation </usage/metrics/open-telemetry>`
        :code:`pip install 'litestar[opentelemetry]'`

    :doc:`SQLAlchemy </usage/databases/sqlalchemy/index>`（通过 `Advanced-Alchemy <https://docs.advanced-alchemy.litestar.dev/latest/>`_）
        :code:`pip install 'litestar[sqlalchemy]'`

    :doc:`Jinja Templating </usage/templating>`
        :code:`pip install 'litestar[jinja]'`

    :doc:`Mako Templating </usage/templating>`
        :code:`pip install 'litestar[mako]'`

    :ref:`Better OpenAPI examples generation <usage/openapi/schema_generation:Generating examples>` with `Polyfactory <https://github.com/litestar-org/polyfactory>`_
        :code:`pip install 'litestar[polyfactory]'`

    :doc:`HTMX plugin </usage/htmx>`
        :code:`pip install 'litestar[htmx]'`

    :ref:`OpenAPI YAML rendering <usage/openapi/ui_plugins:Using OpenAPI UI Plugins>`
        :code:`pip install 'litestar[yaml]'`

    Standard Installation (includes CLI, Uvicorn, and Jinja2 templating):
        :code:`pip install 'litestar[standard]'`

    All Extras:
        :code:`pip install 'litestar[full]'`

    .. note:: 不建议安装全部扩展（full），因为它会带入大量不必要的依赖。

.. _minimal_example:

最小示例
--------

至少请确认已安装 ``litestar[standard]``，它包含 uvicorn。

首先，创建一个名为 ``app.py`` 的文件，内容如下：

.. code-block:: python
   :caption: app.py

   from litestar import Litestar, get


   @get("/")
   async def index() -> str:
       return "Hello, world!"


   @get("/books/{book_id:int}")
   async def get_book(book_id: int) -> dict[str, int]:
       return {"book_id": book_id}


   app = Litestar([index, get_book])

然后，运行以下命令：

.. code-block:: shell

    litestar run
    # 或者直接用 Uvicorn 运行：
    uvicorn app:app --reload

现在你可以在浏览器中访问 ``http://localhost:8000/`` 和 ``http://localhost:8000/books/1``，应能看到两个端点的响应：

.. code-block:: text

   "Hello, world!"

并且

.. code-block:: json

   {"book_id": 1}

.. tip:: 你也可以查看自动生成的基于 OpenAPI 的文档：

    * ``http://localhost:8000/schema``（用于 `ReDoc <https://redocly.com/redoc>`_）
    * ``http://localhost:8000/schema/swagger``（用于 `Swagger UI <https://swagger.io/>`_）
    * ``http://localhost:8000/schema/elements``（用于 `Stoplight Elements <https://stoplight.io/open-source/elements/>`_）
    * ``http://localhost:8000/schema/rapidoc``（用于 `RapiDoc <https://rapidocweb.com/>`_）

你可以在 :doc:`/tutorials/todo-app/index` 部分找到更深入的教程！

扩展示例
--------

**使用 Pydantic 或基于它的库（例如 ormar、beanie、SQLModel）定义你的数据模型**：

.. code-block:: python

    from pydantic import BaseModel, UUID4


    class User(BaseModel):
        first_name: str
        last_name: str
        id: UUID4




你也可以使用 dataclasses（标准库或 Pydantic 支持的 dataclasses）、:class:`typing.TypedDict`，或 :class:`msgspec.Struct`。

.. code-block:: python

   from uuid import UUID

   from dataclasses import dataclass
   from litestar.dto import DTOConfig, DataclassDTO


   @dataclass
   class User:
       first_name: str
       last_name: str
       id: UUID


   class PartialUserDTO(DataclassDTO[User]):
       config = DTOConfig(exclude={"id"}, partial=True)

**为你的数据模型定义一个 Controller：**

.. code-block:: python

    from typing import List

    from litestar import Controller, get, post, put, patch, delete
    from litestar.dto import DTOData
    from pydantic import UUID4

    from my_app.models import User, PartialUserDTO


    class UserController(Controller):
        path = "/users"

        @post()
        async def create_user(self, data: User) -> User: ...

        @get()
        async def list_users(self) -> List[User]: ...

        @patch(path="/{user_id:uuid}", dto=PartialUserDTO)
        async def partial_update_user(
            self, user_id: UUID4, data: DTOData[User]
        ) -> User: ...

        @put(path="/{user_id:uuid}")
        async def update_user(self, user_id: UUID4, data: User) -> User: ...

        @get(path="/{user_id:uuid}")
        async def get_user(self, user_id: UUID4) -> User: ...

        @delete(path="/{user_id:uuid}")
        async def delete_user(self, user_id: UUID4) -> None: ...


在实例化应用时，将 *controller* 导入到应用的入口并传给 Litestar：

.. code-block:: python

   from litestar import Litestar

   from my_app.controllers.user import UserController

   app = Litestar(route_handlers=[UserController])

要 **运行你的应用**，请使用 ASGI 服务器（例如 `uvicorn <https://www.uvicorn.org/>`_）：

.. code-block:: shell

   uvicorn my_app.main:app --reload


理念
----

- Litestar 是一个社区驱动的项目。这意味着项目不是由单一作者维护，
  而是由一个核心维护团队带领，并得到社区贡献者的支持。Litestar 目前有 5 名维护者，并且在积极开发中。
- Litestar 的设计受到 `NestJS <https://nestjs.com/>`_ 的启发 —— 一个当代的 TypeScript 框架 —— 它在设计上包含若干约定与模式。
- 虽然仍支持**基于函数的端点**，Litestar 更侧重于利用 Python 强大的面向对象能力，
  将**基于类的控制器**作为核心设计之一。
- Litestar **不是** 一个微框架。与 FastAPI、Starlette 或 Flask 等框架不同，Litestar 开箱即用地包含许多适合现代 Web 应用的功能，
  如 ORM 集成、客户端与服务端会话、缓存、OpenTelemetry 集成等。它并不打算成为“下一个 Django”（例如，它不会内置自己的 ORM），但它的范围也不是微观的。


与类似框架的功能比较
--------------------

.. csv-table:: Litestar 与其他框架对比
   :file: _static/tables/framework-comparison.csv
   :widths: 5, 35, 15, 15, 15, 15
   :header-rows: 1

示例应用
--------

* `litestar-pg-redis-docker <https://github.com/litestar-org/litestar-pg-redis-docker>`_ ：除了 Litestar 外，展示了应用模块化、SQLAlchemy 2.0 ORM、Redis 缓存等模式。像所有 Litestar 项目一样，该项目欢迎贡献。
* `litestar-fullstack <https://github.com/litestar-org/litestar-fullstack>`_ ：一个功能齐全、面向生产的全栈 Litestar Web 应用，采用最佳实践配置。它包含 SQLAlchemy 2.0、ReactJS、`Vite <https://vitejs.dev/>`_、`SAQ job queue <https://saq-py.readthedocs.io/en/latest/>`_、``Jinja`` 模板等。
  `阅读更多 <https://litestar-org.github.io/litestar-fullstack/latest/>`_。
* `litestar-hello-world <https://github.com/litestar-org/litestar-hello-world>`_: 一个最小化应用示例，适合测试与 POC。
