.. py:currentmodule:: litestar

2.0 有哪些变化?
======================

本文档概述了 **1.51** 版本与 **2.0** 之间的变化。如需详细了解所有变更,包括 2.0 发布前的各版本变更,请查阅 :doc:`/release-notes/changelog`。

Starlite → Litestar
-------------------

我们很高兴在最新版本 2 中带来一些激动人心的变化!最显著的变化是项目更名,原名 Starlite,现在正式更名为 Litestar。

"Starlite"这个名字最初是向 `Starlette <https://www.starlette.io/>`_ 致敬,Starlite 最初基于该 ASGI 框架和工具包。随着开发进展,Starlite 越来越独立,最终在 2022 年 11 月发布的 `v1.39.0 <https://github.com/starlite-api/starlite/releases/tag/v1.39.0>`_ 版本中正式移除了对 Starlette 的依赖。

经过慎重考虑,决定在 2.0 发布时将 Starlite 更名为 Litestar。促成这一决定的因素有很多,主要是社区内外对 *Starlette* 和 *Starlite* 名字相似可能造成混淆的担忧。现在这个名字已经完成了它的历史使命。

****

除了名字,Litestar 2.0 是 Starlite 1.x 的直接继任者,常规发布周期将继续。决定在新名字下发布第一个 2.0 版本,并延续 Starlite 的版本号方案,这样可以最大程度减少迁移摩擦。第一个新名字下的版本是 `v2.0.0alpha3 <https://github.com/litestar-org/litestar/releases/tag/v2.0.0alpha3>`_,紧接着 Starlite 2.0 的最后一个 alpha 版本 `v2.0.0alpha2 <https://github.com/litestar-org/litestar/releases/tag/v2.0.0alpha2>`_。

.. note::
    **1.51** 版本线不受此更名影响

导入路径变化
-------

+----------------------------------------------------+------------------------------------------------------------------------+
| ``1.51``                                           | ``2.x``                                                                |
+====================================================+========================================================================+
| ``starlite.ASGIConnection``                        | :class:`.connection.ASGIConnection`                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Partial``                               | 替换为 DTOs                                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| **枚举**                                                                                                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.RequestEncodingType``                   | :class:`.enums.RequestEncodingType`                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ScopeType``                             | :class:`.enums.ScopeType`                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIMediaType``                      | :class:`.enums.OpenAPIMediaType`                                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| **数据结构**                                                                                                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BackgroundTask``                        | :class:`.background_tasks.BackgroundTask`                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BackgroundTasks``                       | :class:`.background_tasks.BackgroundTasks`                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.State``                                 | :class:`.datastructures.State`                                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ImmutableState``                        | :class:`.datastructures.ImmutableState`                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Cookie``                                | :class:`.datastructures.Cookie`                                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.FormMultiDict``                         | :class:`.datastructures.FormMultiDict`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseHeader``                        | :class:`.datastructures.ResponseHeader`                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.UploadFile``                            | :class:`.datastructures.UploadFile`                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| **配置**                                                                                                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AllowedHostsConfig``                    | :class:`.config.allowed_hosts.AllowedHostsConfig`                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSecurityConfig``                | :class:`.security.AbstractSecurityConfig`                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CacheConfig``                           | :class:`.config.response_cache.ResponseCacheConfig`                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CompressionConfig``                     | :class:`.config.compression.CompressionConfig`                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CORSConfig``                            | :class:`.config.cors.CORSConfig`                                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CSRFConfig``                            | :class:`.config.csrf.CSRFConfig`                                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIConfig``                         | :class:`.openapi.OpenAPIConfig`                                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StaticFilesConfig``                     | ``.static_files.config.StaticFilesConfig``                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TemplateConfig``                        | :class:`.template.TemplateConfig`                                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.BaseLoggingConfig``                     | :class:`.logging.config.BaseLoggingConfig`                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.LoggingConfig``                         | :class:`.logging.config.LoggingConfig`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.StructLoggingConfig``                   | :class:`.logging.config.StructLoggingConfig`                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| **``Provide`` 和分页**                                                                                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Provide``                               | :class:`.di.Provide`                                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ClassicPagination``                     | :class:`.pagination.ClassicPagination`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.CursorPagination``                      | :class:`.pagination.CursorPagination`                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OffsetPagination``                      | :class:`.pagination.OffsetPagination`                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| **响应容器**                                                                                                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.File``                                  | :class:`.response.File`                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Redirect``                              | :class:`.response.Redirect`                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Stream``                                | :class:`.response.Stream`                                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Template``                              | :class:`.response.Template`                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| **异常**                                                                                                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.HTTPException``                         | :class:`.exceptions.HTTPException`                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ImproperlyConfiguredException``         | :class:`.exceptions.ImproperlyConfiguredException`                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.InternalServerException``               | :class:`.exceptions.InternalServerException`                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotFoundException``                     | :class:`.exceptions.NotFoundException`                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.NotAuthorizedException``                | :class:`.exceptions.NotAuthorizedException`                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.PermissionDeniedException``             | :class:`.exceptions.PermissionDeniedException`                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ServiceUnavailableException``           | :class:`.exceptions.ServiceUnavailableException`                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TooManyRequestsException``              | :class:`.exceptions.TooManyRequestsException`                          |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ValidationException``                   | :class:`.exceptions.ValidationException`                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| **测试**                                                                                                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.TestClient``                            | :class:`.testing.TestClient`                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AsyncTestClient``                       | :class:`.testing.AsyncTestClient`                                      |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.RequestFactory``                        | :class:`.testing.RequestFactory`                                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.create_test_client``                    | :func:`.testing.create_test_client`                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.create_async_test_client``              | :func:`.testing.create_async_test_client`                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| **OpenAPI**                                                                                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIController``                     | :class:`.openapi.OpenAPIController`                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.OpenAPIMediaType``                      | :class:`.enums.OpenAPIMediaType`                                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ResponseSpec``                          | :class:`.openapi.spec.ResponseSpec`                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| **中间件**                                                                                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractAuthenticationMiddleware``      | :class:`.middleware.authentication.AbstractAuthenticationMiddleware`   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractMiddleware``                    | :class:`.middleware.base.AbstractMiddleware`                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AuthenticationResult``                  | :class:`.connection.base.AuthenticationResult`                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.DefineMiddleware``                      | :class:`.middleware.base.DefineMiddleware`                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.MiddlewareProtocol``                    | :class:`.types.MiddlewareProtocol`                                     |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.RateLimitConfig``                       | :class:`.middleware.rate_limit.RateLimitConfig`                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.middleware.LoggingMiddlewareConfig``    | :class:`.logging.config.LoggingMiddlewareConfig`                       |
+----------------------------------------------------+------------------------------------------------------------------------+
| **安全**                                                                                                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.AbstractSecurityConfig``                | :class:`.security.AbstractSecurityConfig`                              |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.SessionAuth``                           | :class:`.security.session_auth.SessionAuth`                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.JWTAuth``                               | :class:`.security.jwt.JWTAuth`                                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.JWTCookieAuth``                         | :class:`.security.jwt.JWTCookieAuth`                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.JWT``                                   | :class:`.security.jwt.Token`                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Token``                                 | :class:`.security.jwt.Token`                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.security.jwt.BaseJWTAuth``              | :class:`.security.jwt.JWTAuth`                                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| **路由处理器**                                                                                                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.get``                                   | :func:`.handlers.get`                                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.head``                                  | :func:`.handlers.head`                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.post``                                  | :func:`.handlers.post`                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.patch``                                 | :func:`.handlers.patch`                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.put``                                   | :func:`.handlers.put`                                                  |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.delete``                                | :func:`.handlers.delete`                                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.websocket``                             | :func:`.handlers.websocket`                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.route``                                 | :func:`.handlers.route`                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.asgi``                                  | :func:`.handlers.asgi`                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.HttpRouteHandler``                      | :class:`.handlers.HTTPRouteHandler`                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.ASGIRouteHandler``                      | :class:`.handlers.ASGIRouteHandler`                                    |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.WebsocketRouteHandler``                 | :class:`.handlers.WebsocketRouteHandler`                               |
+----------------------------------------------------+------------------------------------------------------------------------+
| **路由和参数**                                                                                                             |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Litestar``                              | :class:`.app.Litestar`                                                 |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Router``                                | :class:`.router.Router`                                                |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Controller``                            | :class:`.controller.Controller`                                        |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Request``                               | :class:`.connection.Request`                                           |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.WebSocket``                             | :class:`.connection.WebSocket`                                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Response``                              | :class:`.response.Response`                                            |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Websocket``                             | :class:`.connection.WebSocket`                                         |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Body``                                  | :func:`.params.Body`                                                   |
+----------------------------------------------------+------------------------------------------------------------------------+
| ``starlite.Parameter``                             | :func:`.params.Parameter`                                              |
+----------------------------------------------------+------------------------------------------------------------------------+

响应标头
----------------

现在可以使用 :class:`~.datastructures.response_header.ResponseHeader` 的 :class:`Sequence <typing.Sequence>` 或使用普通的 :class:`Mapping[str, str] <typing.Mapping>` 来设置响应标头。:class:`~.datastructures.response_header.ResponseHeader` 的类型也更改为更严格,现在只允许字符串值。

.. code-block:: python
    :caption: 1.51

    from starlite import ResponseHeader, get


    @get(response_headers={"my-header": ResponseHeader(value="header-value")})
    async def handler() -> str: ...


.. code-block:: python
    :caption: 2.x

    from litestar import ResponseHeader, get


    @get(response_headers=[ResponseHeader(name="my-header", value="header-value")])
    async def handler() -> str: ...


    # 或


    @get(response_headers={"my-header": "header-value"})
    async def handler() -> str: ...


响应 Cookie
----------------

响应 cookie 现在也可以使用 :class:`Mapping[str, str] <typing.Mapping>` 设置,类似于 `响应标头`_。

.. code-block:: python

    @get("/", response_cookies=[Cookie(key="foo", value="bar")])
    async def handler() -> None: ...

等同于

.. code-block:: python

    @get("/", response_cookies={"foo": "bar"})
    async def handler() -> None: ...


SQLAlchemy 插件
-----------------

对 SQLAlchemy 1 的支持已被删除,新插件现在仅支持 SQLAlchemy 2。

.. seealso::
    SQLAlchemy 使用文档在 v2 中可用,但 SQLAlchemy 支持在 v3 中移至更全面的独立库。请参阅 `advanced-alchemy 文档 <https://docs.advanced-alchemy.litestar.dev/>`_ 获取 API 参考


移除 Pydantic 模型
--------------------------

几个用于配置的 Pydantic 模型已被 dataclass 或普通类替换。如果您依赖这些模型的隐式数据转换或对它们进行了子类化,您可能需要相应地调整代码。

.. seealso:: :ref:`change:2.0.0alpha1-replace pydantic models with dataclasses`


插件协议
----------------

插件协议已被拆分为三个不同的协议,涵盖不同的用例:

:class:`litestar.plugins.InitPluginProtocol`
    钩入应用程序的初始化过程

``litestar.plugins.SerializationPluginProtocol``
    扩展应用程序的序列化和反序列化功能

``litestar.plugins.OpenAPISchemaPluginProtocol``
    扩展 OpenAPI 架构生成


使用以前 API 所有功能的插件应该简单地从所有三个基类继承。


移除 2 参数 ``before_send``
---------------------------------

``before_send`` 钩子处理器的 2 参数形式已被移除。现有处理器应更改为包含额外的 ``scope`` 参数。


.. code-block:: python
    :caption: 1.51

    async def before_send(message: Message, state: State) -> None: ...


.. code-block:: python
    :caption: 2.x

    async def before_send(message: Message, state: State, scope: Scope) -> None: ...


.. seealso::
    :ref:`change:2.0.0alpha2-remove support for 2 argument form of` ``before_send`` 和 :ref:`before_send` API 参考


``initial_state`` 应用程序参数
---------------------------------------

:class:`~litestar.app.Litestar` 的 ``initial_state`` 参数已被 ``state`` 关键字参数替换,接受可选的 :class:`~litestar.datastructures.state.State` 实例。

使用此关键字参数的现有代码需要从

.. code-block:: python
    :caption: 1.51

    app = Starlite(..., initial_state={"some": "key"})

更改为

.. code-block:: python
    :caption: 2.x

    app = Litestar(..., state=State({"some": "key"}))


存储
------

引入了新模块 ``litestar.stores``,它替换了以前使用的 ``starlite.cache.Cache`` 和服务器端会话存储后端。

这些存储为常见的键/值存储(如 Redis)和内存实现提供了低级异步接口。它们目前用于服务器端会话、缓存和速率限制。

存储通过 :class:`~.stores.registry.StoreRegistry` 集成到 :class:`~app.Litestar` 应用程序对象中,可用于注册和访问存储以及提供默认值。

.. literalinclude:: /examples/stores/get_set.py
    :language: python

.. literalinclude:: /examples/stores/namespacing.py
    :language: python
    :caption: 使用命名空间

.. literalinclude:: /examples/stores/registry.py
    :language: python
    :caption: 使用注册表

.. seealso:: :doc:`/usage/stores` 使用文档


``stores`` 用于缓存和其他集成
-----------------------------------------------------------

新引入的 :doc:`stores </usage/stores>` 在各个地方取代了已删除的 ``starlite.cache`` 模块。

以下现在使用存储:

- :class:`~litestar.middleware.rate_limit.RateLimitMiddleware`
- :class:`~litestar.config.response_cache.ResponseCacheConfig`
- :class:`~litestar.middleware.session.server_side.ServerSideSessionConfig`

以下属性已重命名以减少歧义:

- ``Starlite.cache_config`` > ``Litestar.response_cache_config``
- ``AppConfig.cache_config`` > :attr:`~litestar.config.app.AppConfig.response_cache_config`

此外,``ASGIConnection.cache`` 属性已被移除。它可以通过直接访问存储来替换,如 :doc:`stores </usage/stores>` 中所述


DTO
----

数据传输对象现在使用处理器/控制器/路由器和应用程序的 ``dto`` 和 ``return_dto`` 参数定义。

DTO 是任何继承自 :class:`litestar.dto.base_dto.AbstractDTO` 的类型。

Litestar 提供了一套实现 ``AbstractDTO`` 抽象类的类型,可用于定义 DTO:

- :class:`litestar.dto.dataclass_dto.DataclassDTO`
- :class:`litestar.dto.msgspec_dto.MsgspecDTO`
- :class:`advanced_alchemy.extensions.litestar.dto.SQLAlchemyDTO`
- :class:`litestar.contrib.pydantic.PydanticDTO`
- :class:`!litestar.contrib.piccolo.PiccoloDTO`

例如,从 dataclass 定义 DTO:

.. code-block:: python

    from dataclasses import dataclass

    from litestar import get
    from litestar.dto import DTOConfig, DataclassDTO


    @dataclass
    class MyType:
        some_field: str
        another_field: int


    class MyDTO(DataclassDTO[MyType]):
        config = DTOConfig(exclude={"another_field"})


    @get(dto=MyDTO)
    async def handler() -> MyType:
        return MyType(some_field="some value", another_field=42)


.. literalinclude:: /examples/data_transfer_objects/the_return_dto_parameter.py
    :language: python

.. literalinclude:: /examples/data_transfer_objects/factory/renaming_fields.py
    :language: python
    :caption: 重命名字段

.. literalinclude:: /examples/data_transfer_objects/factory/excluding_fields.py
    :language: python
    :caption: 排除字段

.. literalinclude:: /examples/data_transfer_objects/factory/marking_fields.py
    :language: python
    :caption: 标记字段

.. seealso::
    :doc:`/usage/dto/index` 使用文档


应用程序生命周期钩子
--------------------------

所有应用程序生命周期钩子已合并到 ``on_startup`` 和 ``on_shutdown`` 中。以下钩子已被移除:

- ``before_startup``
- ``after_startup``
- ``before_shutdown``
- ``after_shutdown``


``on_startup`` 和 ``on_shutdown`` 现在可选地接收应用程序实例作为其第一个参数。如果您的 ``on_startup`` 和 ``on_shutdown`` 钩子使用了应用程序状态,它们现在必须通过提供的应用程序实例访问它。

.. code-block:: python
    :caption: 1.51

    def on_startup(state: State) -> None:
        print(state.something)


.. code-block:: python
    :caption: 2.x

    def on_startup(app: Litestar) -> None:
        print(app.state.something)


无需 ``Provide`` 的依赖
--------------------------------

依赖现在可以在不使用 :class:`~litestar.di.Provide` 的情况下声明,直接传递可调用对象。在不需要 :class:`~litestar.di.Provide` 配置选项的地方,这可能是有利的。

.. code-block:: python

    async def some_dependency() -> str: ...


    app = Litestar(dependencies={"some": Provide(some_dependency)})

等同于

.. code-block:: python

    async def some_dependency() -> str: ...


    app = Litestar(dependencies={"some": some_dependency})


``sync_to_thread``
------------------

``sync_to_thread`` 选项可用于在线程池中运行提供给路由处理器或 :class:`~litestar.di.Provide` 的同步可调用对象。由于在不使用 ``sync_to_thread=True`` 时同步函数可能阻塞主线程,因此在这些情况下会引发警告。如果同步函数不应在线程池中运行,传递 ``sync_to_thread=False`` 也会消除警告。

.. tip::
    可以通过设置环境变量 ``LITESTAR_WARN_IMPLICIT_SYNC_TO_THREAD=0`` 完全禁用警告


.. code-block:: python
    :caption: 1.51

    @get()
    def handler() -> None: ...


.. code-block:: python
    :caption: 2.x

    @get(sync_to_thread=False)
    def handler() -> None: ...

或

.. code-block:: python
    :caption: 2.x

    @get(sync_to_thread=True)
    def handler() -> None: ...


.. seealso::
    :doc:`/topics/sync-vs-async` 主题指南


HTMX
----

通过 ``litestar.contrib.htmx`` 模块添加了对 HTMX 请求和响应的基本支持。

.. seealso::
    :doc:`/usage/htmx` 使用文档


事件总线
---------

Litestar 的简单事件总线系统,支持同步和异步监听器和发射器,提供与处理器类似的接口。它目前具有一个简单的内存进程本地后端。


.. seealso::
    :doc:`/usage/events` 使用文档和 :doc:`/reference/events` API 参考


增强的 WebSocket 支持
--------------------------

一套用于处理 WebSocket 的新功能,包括自动连接处理、类似于路由处理器的传入和传出数据的(反)序列化、基于 OOP 的事件调度、数据迭代器等。

.. literalinclude:: /examples/websockets/listener_class_based.py
    :caption: 使用基于类的监听器
    :language: python

.. literalinclude:: /examples/websockets/mode_send_text.py
    :caption: 回显文本
    :language: python

.. literalinclude:: /examples/websockets/sending_json_dataclass.py
    :caption: 在 dataclass 中包装数据
    :language: python

.. literalinclude:: /examples/websockets/with_dto.py
    :language: python

.. code-block:: python
    :caption: 接收 JSON 并作为 MessagePack 发送回

    from litestar import websocket, WebSocket


    @websocket("/")
    async def handler(socket: WebSocket) -> None:
        await socket.accept()
        async for message in socket.iter_data(mode):
            await socket.send_msgpack(message)


.. seealso::
    * :ref:`change:2.0.0alpha3-enhanced websockets support`
    * :ref:`change:2.0.0alpha6-websockets: managing a socket's lifespan using a context manager in websocket listeners`
    * :ref:`change:2.0.0alpha6-websockets: messagepack support`
    * :ref:`change:2.0.0alpha6-websockets: data iterators`
    * :doc:`/usage/websockets` 使用文档


Attrs 签名建模
-------------------------

``attrs`` 类支持在路由处理器中作为类型。


路由处理器中的 :class:`~typing.Annotated` 支持
----------------------------------------------------

:class:`Annotated <typing.Annotated>` 现在可以在路由处理器和依赖中使用,以指定有关字段的附加信息

.. code-block:: python

    @get("/")
    def index(param: int = Parameter(gt=5)) -> dict[str, int]: ...

现在可以写作

.. code-block:: python

    @get("/")
    def index(param: Annotated[int, Parameter(gt=5)]) -> dict[str, int]: ...


通道
---------

:doc:`/usage/channels` 是一个通用的事件流模块,例如可用于通过 WebSocket 广播消息,并包括自动生成 WebSocket 路由处理器以广播消息等功能。

.. literalinclude:: /examples/channels/run_in_background.py
    :language: python

.. seealso::
    :doc:`channels </usage/channels>` 使用文档


应用程序生命周期上下文管理器
--------------------------------------

:class:`~litestar.app.Litestar` 添加了新的 ``lifespan`` 参数,接受异步上下文管理器,包装应用程序的生命周期。它将在启动阶段进入,在关闭时退出,提供与 ``on_startup`` 和 ``on_shutdown`` 钩子相同的功能。


.. literalinclude:: /examples/application_hooks/lifespan_manager.py
    :language: python


响应类型
--------------

Starlite 有响应容器的概念,这些是用于指示处理器返回的响应类型的数据类型。这些包括 ``File``、``Redirect``、``Template`` 和 ``Stream`` 类型。这些类型将响应接口从底层响应本身抽象出来。

在 Litestar 中,这些类型仍然存在,但它们现在是 :class:`Response <.response.Response>` 的子类,并从 ``litestar.response`` 模块导入。与 Starlite 的响应容器相比,这些类型对于与传出响应交互更有用,例如添加标头和 cookie 的方法。否则,它们的使用应该与 Starlite 非常相似。

Litestar 还引入了基于 :class:`ASGIResponse <.response.base.ASGIResponse>` 的新 ASGI 响应类型层。这些类型将响应表示为不可变对象,并由 Litestar 内部使用以执行响应的 I/O 操作。这些可以从处理器创建和返回,但它们是低级的,缺少高级响应类型的实用性。
