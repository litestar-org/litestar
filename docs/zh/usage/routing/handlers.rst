==============
路由处理器
==============

路由处理器是 Litestar 的核心。它们是通过使用从 Litestar 导出的处理器 :term:`装饰器 <decorator>` 来装饰函数或类方法来构造的。

例如：

.. code-block:: python
    :caption: 使用 :func:`@get() <.handlers.get>` :term:`装饰器 <decorator>` 装饰函数来定义路由处理器

    from litestar import get


    @get("/")
    def greet() -> str:
       return "hello world"

在上面的示例中，:term:`装饰器 <decorator>` 包含了为路径 ``"/"`` 和 HTTP 动词 ``GET`` 的组合定义端点操作所需的所有信息。
在这种情况下，它将是一个带有 ``Content-Type`` 头为 ``text/plain`` 的 HTTP 响应。

.. include:: /admonitions/sync-to-thread-info.rst

声明路径
--------

所有路由处理器 :term:`装饰器 <decorator>` 都接受一个可选的路径 :term:`参数 <argument>`。
这个 :term:`参数 <argument>` 可以使用 :paramref:`~.handlers.base.BaseRouteHandler.path` 参数作为
:term:`关键字参数 <argument>` 声明：

.. code-block:: python
    :caption: 通过将路径作为关键字参数传递来定义路由处理器

    from litestar import get


    @get(path="/some-path")
    async def my_route_handler() -> None: ...

它也可以作为 :term:`参数 <argument>` 传递而不使用关键字：

.. code-block:: python
    :caption: 定义路由处理器但不使用关键字参数

    from litestar import get


    @get("/some-path")
    async def my_route_handler() -> None: ...

这个 :term:`参数 <argument>` 的值可以是字符串路径（如上面的示例），也可以是 :class:`list` 类型的
:class:`字符串 <str>` 路径：

.. code-block:: python
    :caption: 定义具有多个路径的路由处理器

    from litestar import get


    @get(["/some-path", "/some-other-path"])
    async def my_route_handler() -> None: ...

当您想要拥有可选的 :ref:`路径参数 <usage/routing/parameters:Path Parameters>` 时，这特别有用：

.. code-block:: python
    :caption: 定义具有可选路径参数的路径的路由处理器

    from litestar import get


    @get(
       ["/some-path", "/some-path/{some_id:int}"],
    )
    async def my_route_handler(some_id: int = 1) -> None: ...

.. _handler-function-kwargs:

"保留" 关键字参数
-----------------

路由处理器函数或方法通过将这些数据声明为带注解的函数 :term:`关键字参数 <argument>` 来访问各种数据。
Litestar 会检查带注解的 :term:`关键字参数 <argument>`，然后将它们注入到请求处理器中。

可以使用带注解的函数 :term:`关键字参数 <argument>` 访问以下来源：

- :ref:`路径、查询、头和 cookie 参数 <usage/routing/parameters:the parameter function>`
- :doc:`请求 </usage/requests>`
- :doc:`注入的依赖项 </usage/dependency-injection>`

此外，您可以指定以下特殊的 :term:`关键字参数 <argument>`（称为"保留关键字"）：

* ``cookies``: 将请求 :class:`cookies <.datastructures.cookie.Cookie>` 作为解析后的 :class:`字典 <dict>` 注入。
* ``headers``: 将请求头作为解析后的 :class:`字典 <dict>` 注入。
* ``query``: 将请求 ``query_params`` 作为解析后的 :class:`字典 <dict>` 注入。
* ``request``: 注入 :class:`Request <.connection.Request>` 实例。仅适用于 `HTTP 路由处理器`_
* ``scope``: 注入 ASGI 作用域 :class:`字典 <dict>`。
* ``socket``: 注入 :class:`WebSocket <.connection.WebSocket>` 实例。仅适用于 `websocket 路由处理器`_
* ``state``: 注入应用程序 :class:`State <.datastructures.state.State>` 的副本。
* ``body``: 原始请求体。仅适用于 `HTTP 路由处理器`_

请注意，如果您的参数与上面任何保留的 :term:`关键字参数 <argument>` 冲突，您可以
:ref:`提供一个替代名称 <usage/routing/parameters:Alternative names and constraints>`。

例如：

.. code-block:: python
    :caption: 为保留关键字参数提供替代名称

    from typing import Any, Dict
    from litestar import Request, get
    from litestar.datastructures import Headers, State


    @get(path="/")
    async def my_request_handler(
       state: State,
       request: Request,
       headers: Dict[str, str],
       query: Dict[str, Any],
       cookies: Dict[str, Any],
    ) -> None: ...

.. tip:: 您可以为应用程序状态定义自定义类型，然后将其用作类型，而不是仅使用 Litestar 的
    :class:`~.datastructures.state.State` 类

类型注解
--------

Litestar 强制执行严格的 :term:`类型注解 <annotation>`。
由路由处理器装饰的函数 **必须** 对其所有 :term:`参数 <argument>` 和返回值进行类型注解。

如果缺少类型注解，将在应用程序启动过程中引发 :exc:`~.exceptions.ImproperlyConfiguredException`。

强制执行此限制有几个原因：

#. 确保最佳实践
#. 确保一致的 OpenAPI 模式生成
#. 允许 Litestar 在应用程序引导期间计算函数所需的 :term:`参数 <argument>`

HTTP 路由处理器
----------------

:class:`~.handlers.HTTPRouteHandler` 用于处理 HTTP 请求，可以使用 :func:`~.handlers.route` :term:`装饰器 <decorator>` 创建：

.. code-block:: python
    :caption: 使用 :func:`@route() <.handlers.route>` :term:`装饰器 <decorator>` 装饰函数来定义路由处理器

    from litestar import HttpMethod, route


    @route(path="/some-path", http_method=[HttpMethod.GET, HttpMethod.POST])
    async def my_endpoint() -> None: ...

也可以不使用装饰器，直接使用 ``HTTPRouteHandler`` 来实现相同的效果：

.. code-block:: python
    :caption: 通过创建 :class:`HTTPRouteHandler <.handlers.HTTPRouteHandler>` 实例来定义路由处理器

    from litestar import HttpMethod
    from litestar.handlers.http_handlers import HTTPRouteHandler


    async def my_endpoint() -> None: ...

    handler = HTTPRouteHandler(
        path="/some-path",
        http_method=[HttpMethod.GET, HttpMethod.POST],
        fn=my_endpoint
    )


语义处理器 :term:`装饰器 <decorator>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Litestar 还包括"语义" :term:`装饰器 <decorator>`，即预先设置了
:paramref:`~litestar.handlers.HTTPRouteHandler.http_method` :term:`关键字参数 <argument>` 为特定 HTTP 动词的
:term:`装饰器 <decorator>`，这与它们的名称相关：

* :func:`@delete() <.handlers.delete>`
* :func:`@get() <.handlers.get>`
* :func:`@head() <.handlers.head>`
* :func:`@patch() <.handlers.patch>`
* :func:`@post() <.handlers.post>`
* :func:`@put() <.handlers.put>`

这些的使用方式与 :func:`@route() <.handlers.route>` 完全相同，唯一的例外是您不需要配置
:paramref:`~.handlers.HTTPRouteHandler.http_method` :term:`关键字参数 <argument>`：

.. dropdown:: 点击查看预定义的路由处理器

    .. code-block:: python
        :caption: HTTP 路由处理器的预定义 :term:`装饰器 <decorator>`

        from litestar import delete, get, patch, post, put, head
        from litestar.dto import DTOConfig, DTOData
        from litestar.plugins.pydantic import PydanticDTO

        from pydantic import BaseModel


        class Resource(BaseModel): ...


        class PartialResourceDTO(PydanticDTO[Resource]):
           config = DTOConfig(partial=True)


        @get(path="/resources")
        async def list_resources() -> list[Resource]: ...


        @post(path="/resources")
        async def create_resource(data: Resource) -> Resource: ...


        @get(path="/resources/{pk:int}")
        async def retrieve_resource(pk: int) -> Resource: ...


        @head(path="/resources/{pk:int}")
        async def retrieve_resource_head(pk: int) -> None: ...


        @put(path="/resources/{pk:int}")
        async def update_resource(data: Resource, pk: int) -> Resource: ...


        @patch(path="/resources/{pk:int}", dto=PartialResourceDTO)
        async def partially_update_resource(
           data: DTOData[PartialResourceDTO], pk: int
        ) -> Resource: ...


        @delete(path="/resources/{pk:int}")
        async def delete_resource(pk: int) -> None: ...

此外，在 OpenAPI 规范中，HTTP 动词（例如 ``GET``、``POST`` 等）和路径的每个唯一组合
都被视为一个独立的 `操作 <https://spec.openapis.org/oas/latest.html#operation-object>`_，
每个操作都应通过唯一的 :paramref:`~.handlers.HTTPRouteHandler.operation_id` 来区分，
并且最好还应有 :paramref:`~.handlers.HTTPRouteHandler.summary` 和
:paramref:`~.handlers.HTTPRouteHandler.description` 部分。

因此，不鼓励使用 :func:`@route() <.handlers.route>` :term:`装饰器 <decorator>`。
相反，首选模式是使用辅助类方法共享代码或将代码抽象为可重用的函数。

Websocket 路由处理器
---------------------

可以使用 :func:`@websocket() <.handlers.WebsocketRouteHandler>` 路由处理器来处理 WebSocket 连接。

.. note:: websocket 处理器是一种低级方法，需要直接处理套接字，
    并处理保持它打开、异常、客户端断开连接和内容协商。

    有关处理 WebSocket 的更高级方法，请参阅 :doc:`/usage/websockets`

.. code-block:: python
    :caption: 使用 :func:`@websocket() <.handlers.WebsocketRouteHandler>` 路由处理器 :term:`装饰器 <decorator>`

    from litestar import WebSocket, websocket


    @websocket(path="/socket")
    async def my_websocket_handler(socket: WebSocket) -> None:
       await socket.accept()
       await socket.send_json({...})
       await socket.close()

:func:`@websocket() <.handlers.WebsocketRouteHandler>` :term:`装饰器 <decorator>` 可用于创建
:class:`~.handlers.WebsocketRouteHandler` 的实例。因此，以下代码与上面的代码等效：

.. code-block:: python
    :caption: 直接使用 :class:`~.handlers.WebsocketRouteHandler` 类

    from litestar import WebSocket
    from litestar.handlers.websocket_handlers import WebsocketRouteHandler

    async def my_websocket_handler(socket: WebSocket) -> None:
       await socket.accept()
       await socket.send_json({...})
       await socket.close()

    my_websocket_handler = WebsocketRouteHandler(
        path="/socket",
        fn=my_websocket_handler,
    )

与 HTTP 路由处理器不同，websocket 处理器有以下要求：

#. 它们 **必须** 声明一个 ``socket`` :term:`关键字参数 <argument>`。
#. 它们 **必须** 具有 ``None`` 的返回 :term:`注解 <annotation>`。
#. 它们 **必须** 是 :ref:`async 函数 <python:async def>`。

这些要求使用检查来强制执行，如果不满足任何一个要求，将引发有信息的异常。

OpenAPI 目前不支持 websockets。因此不会为这些路由处理器生成模式。

.. seealso:: * :class:`~.handlers.WebsocketRouteHandler`
    * :doc:`/usage/websockets`

ASGI 路由处理器
----------------

如果您需要编写自己的 ASGI 应用程序，可以使用 :func:`@asgi() <.handlers.asgi>` :term:`装饰器 <decorator>`：

.. code-block:: python
    :caption: 使用 :func:`@asgi() <.handlers.asgi>` 路由处理器 :term:`装饰器 <decorator>`

    from litestar.types import Scope, Receive, Send
    from litestar.status_codes import HTTP_400_BAD_REQUEST
    from litestar import Response, asgi


    @asgi(path="/my-asgi-app")
    async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
       if scope["type"] == "http":
           if scope["method"] == "GET":
               response = Response({"hello": "world"})
               await response(scope=scope, receive=receive, send=send)
           return
       response = Response(
           {"detail": "unsupported request"}, status_code=HTTP_400_BAD_REQUEST
       )
       await response(scope=scope, receive=receive, send=send)

:func:`@asgi() <.handlers.asgi>` :term:`装饰器 <decorator>` 可用于创建
:class:`~.handlers.ASGIRouteHandler` 的实例。因此，以下代码与上面的代码等效：

.. code-block:: python
    :caption: 直接使用 :class:`~.handlers.ASGIRouteHandler` 类

    from litestar import Response
    from litestar.handlers.asgi_handlers import ASGIRouteHandler
    from litestar.status_codes import HTTP_400_BAD_REQUEST
    from litestar.types import Scope, Receive, Send

    async def my_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
       if scope["type"] == "http":
           if scope["method"] == "GET":
               response = Response({"hello": "world"})
               await response(scope=scope, receive=receive, send=send)
           return
       response = Response(
           {"detail": "unsupported request"}, status_code=HTTP_400_BAD_REQUEST
       )
       await response(scope=scope, receive=receive, send=send)

    my_asgi_app = ASGIRouteHandler(path="/my-asgi-app", fn=my_asgi_app)


ASGI 路由处理器注意事项
~~~~~~~~~~~~~~~~~~~~~~~~

与其他路由处理器不同，:func:`@asgi() <.handlers.asgi>` 路由处理器只接受三个
**必须** 定义的 :term:`关键字参数 <argument>`：

* ``scope``，描述 ASGI 连接的值映射。它总是包含一个 ``type`` 键，值为
  ``http`` 或 ``websocket``，以及一个 ``path`` 键。如果类型是 ``http``，scope 字典还将包括
  一个 ``method`` 键，值为 ``DELETE``、``GET``、``POST``、``PATCH``、``PUT``、``HEAD`` 之一。
* ``receive``，ASGI 应用程序接收消息的注入函数。
* ``send``，ASGI 应用程序发送消息的注入函数。

您可以在 `ASGI 规范 <https://asgi.readthedocs.io/en/latest/specs/main.html>`_ 中阅读更多相关信息。

此外，ASGI 路由处理器函数 **必须** 是 :ref:`async 函数 <python:async def>`。
这使用检查来强制执行，如果函数不是 :ref:`async 函数 <python:async def>`，
将引发有信息的异常。

有关 :func:`@asgi() <.handlers.asgi>` :term:`装饰器 <decorator>` 及其接受的 :term:`关键字参数 <argument>` 的完整详细信息，
请参阅 :class:`ASGIRouteHandler API 参考文档 <.handlers.asgi_handlers.ASGIRouteHandler>`。

路由处理器索引
--------------

您可以在所有路由处理器 :term:`装饰器 <decorator>` 中提供一个 :paramref:`~.handlers.base.BaseRouteHandler.name`
:term:`关键字参数 <argument>`。此 :term:`关键字参数 <argument>` 的值 **必须是唯一的**，
否则将引发 :exc:`~.exceptions.ImproperlyConfiguredException` 异常。

:paramref:`~.handlers.base.BaseRouteHandler.name` 的默认值是处理器的 :meth:`~object.__str__` 方法返回的值，
它应该是处理器的完整点分路径（例如，对于位于 ``app/controllers/projects.py`` 文件中的 ``list`` 函数，
应该是 ``app.controllers.projects.list``）。
:paramref:`~.handlers.base.BaseRouteHandler.name` 可用于在运行时动态检索包含路由处理器实例和路径的映射，
也可用于为该处理器构建 URL 路径：

.. code-block:: python
    :caption: 使用 :paramref:`~.handlers.base.BaseRouteHandler.name` :term:`关键字参数 <argument>` 检索路由处理器实例和路径

    from litestar import Litestar, Request, get
    from litestar.exceptions import NotFoundException
    from litestar.response import Redirect


    @get("/abc", name="one")
    def handler_one() -> None:
        pass


    @get("/xyz", name="two")
    def handler_two() -> None:
        pass


    @get("/def/{param:int}", name="three")
    def handler_three(param: int) -> None:
        pass


    @get("/{handler_name:str}", name="four")
    def handler_four(request: Request, name: str) -> Redirect:
        handler_index = request.app.get_handler_index_by_name(name)
        if not handler_index:
            raise NotFoundException(f"no handler matching the name {name} was found")

        # handler_index == { "paths": ["/"], "handler": ..., "qualname": ... }
        # 在下面对处理器索引做一些操作，例如发送重定向响应到处理器，或访问
        # handler.opt 和存储在那里的一些值等。

        return Redirect(path=handler_index[0])


    @get("/redirect/{param_value:int}", name="five")
    def handler_five(request: Request, param_value: int) -> Redirect:
        path = request.app.route_reverse("three", param=param_value)
        return Redirect(path=path)


    app = Litestar(route_handlers=[handler_one, handler_two, handler_three])

如果未找到具有给定名称的路由，或者缺少任何路径 :term:`参数 <parameter>`，
或者传递的任何路径 :term:`参数 <parameter>` 类型与相应路由声明中的类型不匹配，
:meth:`~.app.Litestar.route_reverse` 将引发 :exc:`~.exceptions.NoRouteMatchFoundException`。

但是，:class:`str` 可以代替 :class:`~datetime.datetime`、:class:`~datetime.date`、
:class:`~datetime.time`、:class:`~datetime.timedelta`、:class:`float` 和 :class:`~pathlib.Path`
参数被接受，因此您可以应用自定义格式并将结果传递给 :meth:`~.app.Litestar.route_reverse`。

如果处理器附加了多个路径，:meth:`~.app.Litestar.route_reverse` 将返回消耗传递给函数的
:term:`关键字参数 <argument>` 数量最多的路径。

.. code-block:: python
    :caption: 使用 :meth:`~.app.Litestar.route_reverse` 方法为路由处理器构建 URL 路径

    from litestar import get, Request


    @get(
       ["/some-path", "/some-path/{id:int}", "/some-path/{id:int}/{val:str}"],
       name="handler_name",
    )
    def handler(id: int = 1, val: str = "default") -> None: ...


    @get("/path-info")
    def path_info(request: Request) -> str:
       path_optional = request.app.route_reverse("handler_name")
       # /some-path`

       path_partial = request.app.route_reverse("handler_name", id=100)
       # /some-path/100

       path_full = request.app.route_reverse("handler_name", id=100, val="value")
       # /some-path/100/value`

       return f"{path_optional} {path_partial} {path_full}"

当处理器与具有相同路径 :term:`参数 <parameter>` 的多个路由相关联时
（例如，在多个路由器上注册的索引处理器），:meth:`~.app.Litestar.route_reverse` 的输出是不可预测的。
此 :term:`callable` 将返回格式化的路径；但是，其选择可能看起来是任意的。
因此，**强烈** 建议不要在这些条件下反转 URL。

如果您有权访问 :class:`~.connection.Request` 实例，您可以使用 :meth:`~.connection.ASGIConnection.url_for` 方法进行反向查找，
该方法类似于 :meth:`~.app.Litestar.route_reverse`，但返回绝对 URL。

.. _handler_opts:

向处理器添加任意元数据
----------------------

所有路由处理器 :term:`装饰器 <decorator>` 都接受一个名为 ``opt`` 的键，它接受一个
:term:`字典 <dict>`，其中包含任意值，例如：

.. code-block:: python
    :caption: 通过 ``opt`` :term:`关键字参数 <argument>` 向路由处理器添加任意元数据

    from litestar import get


    @get("/", opt={"my_key": "some-value"})
    def handler() -> None: ...

此字典可以由 :doc:`路由守卫 </usage/security/guards>` 访问，或通过访问 :class:`~.connection.request.Request` 对象上的
:attr:`~.connection.ASGIConnection.route_handler` 属性，或直接使用 :class:`ASGI scope <litestar.types.Scope>` 对象访问。

基于 ``opt``，您可以将任何任意 :term:`关键字参数 <argument>` 传递给路由处理器 :term:`装饰器 <decorator>`，
它将自动设置为 ``opt`` 字典中的键：

.. code-block:: python
    :caption: 通过 ``opt`` :term:`关键字参数 <argument>` 向路由处理器添加任意元数据

    from litestar import get


    @get("/", my_key="some-value")
    def handler() -> None: ...


    assert handler.opt["my_key"] == "some-value"

您可以在应用程序的所有层指定 ``opt`` :term:`字典 <dict>`。
在特定路由处理器、控制器、路由器上，甚至在应用程序实例本身上，
如 :ref:`分层架构 <usage/applications:layered architecture>` 中所述。

生成的 :term:`字典 <dict>` 是通过合并所有层的 ``opt`` 字典构造的。
如果多个层定义相同的键，则离响应处理器最近的层的值将优先。

.. _signature_namespace:

签名 :term:`命名空间 <namespace>`
---------------------------------

Litestar 为任何处理器或依赖函数的参数生成一个模型，称为"签名模型"，
用于解析和验证要注入函数的原始数据。

构建模型需要在运行时检查签名参数的名称和类型，因此类型必须在模块的作用域内可用 -
这是 linting 工具（如 ``ruff`` 或 ``flake8-type-checking``）会主动监视并提出建议的内容。

例如，在以下代码段中，名称 ``Model`` 在运行时 *不* 可用：

.. code-block:: python
    :caption: 具有在运行时不可用的类型的路由处理器

    from __future__ import annotations

    from typing import TYPE_CHECKING

    from litestar import Controller, post

    if TYPE_CHECKING:
        from domain import Model


    class MyController(Controller):
        @post()
        def create_item(data: Model) -> Model:
            return data

在此示例中，Litestar 将无法生成签名模型，因为类型 ``Model`` 在运行时不存在于模块作用域中。
我们可以通过逐个情况消除 linter，例如：

.. code-block:: python
    :no-upgrade:
    :caption: 为在运行时不可用的类型消除 linter

    from __future__ import annotations

    from typing import TYPE_CHECKING

    from litestar import Controller, post

    # 根据您的 linter 选择适当的 noqa 指令
    from domain import Model  # noqa: TCH002

然而，这种方法可能会变得乏味；作为替代方案，Litestar 在应用程序的每个 :ref:`层 <layered-architecture>` 上接受一个 ``signature_types`` 序列，
如以下示例所示：

.. literalinclude:: /examples/signature_namespace/domain.py
    :language: python
    :caption: 此模块在某个中心位置定义我们的域类型。

此模块定义了我们的控制器，请注意，我们不将 ``Model`` 导入到运行时 :term:`命名空间 <namespace>`，
也不需要任何指令来控制 linter 的行为。

.. literalinclude:: /examples/signature_namespace/controller.py
    :language: python
    :caption: 此模块定义了我们的控制器，而无需将 ``Model`` 导入到运行时命名空间。

最后，我们确保我们的应用程序知道，当它在解析签名时遇到名称"Model"时，
它应该引用我们的域 ``Model`` 类型。

.. literalinclude:: /examples/signature_namespace/app.py
    :language: python
    :caption: 确保应用程序知道在解析签名时如何解析 ``Model`` 类型。

.. tip:: 如果您想将类型映射到与其 ``__name__`` 属性不同的名称，
    您可以使用 :paramref:`~.handlers.base.BaseRouteHandler.signature_namespace` 参数，
    例如，``app = Litestar(signature_namespace={"FooModel": Model})``。

    这使得可以在 ``if TYPE_CHECKING`` 块内使用类似 ``from domain.foo import Model as FooModel`` 的导入模式。

默认签名 :term:`命名空间 <namespace>`
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Litestar 在解析签名模型时自动将一些名称添加到签名 :term:`命名空间 <namespace>`，
以支持 :ref:`handler-function-kwargs` 的注入。

这些名称是：

* ``Headers``
* ``ImmutableState``
* ``Receive``
* ``Request``
* ``Scope``
* ``Send``
* ``State``
* ``WebSocket``
* ``WebSocketScope``

这些名称中的任何一个的导入都可以安全地留在 ``if TYPE_CHECKING:`` 块中，无需任何配置。
