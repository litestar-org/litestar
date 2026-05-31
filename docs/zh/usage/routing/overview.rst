========
路由概述
========

注册路由
--------

在每个 Litestar 应用的根部，都有一个 :class:`Litestar <litestar.app.Litestar>` 类的实例，
在其上注册根级别的 :class:`控制器 <.controller.Controller>`、:class:`路由器 <.router.Router>`
和 :class:`路由处理器 <.handlers.BaseRouteHandler>` 函数，使用
:paramref:`~litestar.config.app.AppConfig.route_handlers` :term:`关键字参数 <argument>`：

.. code-block:: python
    :caption: 注册路由处理器

    from litestar import Litestar, get


    @get("/sub-path")
    def sub_path_handler() -> None: ...


    @get()
    def root_handler() -> None: ...


    app = Litestar(route_handlers=[root_handler, sub_path_handler])

在应用上注册的组件会被追加到根路径。因此，``root_handler`` 函数将在路径 ``"/"`` 上被调用，
而 ``sub_path_handler`` 将在 ``"/sub-path"`` 上被调用。

您也可以声明一个函数来处理多个路径，例如：

.. code-block:: python
    :caption: 为多个路径注册路由处理器

    from litestar import get, Litestar


    @get(["/", "/sub-path"])
    def handler() -> None: ...


    app = Litestar(route_handlers=[handler])

要处理更复杂的路径模式，您应该使用 :class:`控制器 <.controller.Controller>` 和
:class:`路由器 <.router.Router>`

动态注册路由
^^^^^^^^^^^^

有时需要动态注册路由。Litestar 通过 Litestar 应用实例暴露的
:paramref:`~.app.Litestar.register` 方法支持此功能：

.. code-block:: python
    :caption: 使用 :paramref:`~.app.Litestar.register` 方法动态注册路由处理器

    from litestar import Litestar, get


    @get()
    def root_handler() -> None: ...


    app = Litestar(route_handlers=[root_handler])


    @get("/sub-path")
    def sub_path_handler() -> None: ...


    app.register(sub_path_handler)

由于应用实例被附加到 :class:`~.connection.base.ASGIConnection`、
:class:`~.connection.request.Request` 和 :class:`~.connection.websocket.WebSocket` 对象的所有实例，
因此您实际上可以在路由处理器函数、中间件甚至注入的依赖项内部调用 :meth:`~.router.Router.register` 方法。例如：

.. code-block:: python
    :caption: 从路由处理器函数内部调用 :meth:`~.router.Router.register` 方法

    from typing import Any
    from litestar import Litestar, Request, get


    @get("/some-path")
    def route_handler(request: Request[Any, Any]) -> None:
       @get("/sub-path")
       def sub_path_handler() -> None: ...

       request.app.register(sub_path_handler)


    app = Litestar(route_handlers=[route_handler])

在上面的示例中，我们动态创建了 ``sub_path_handler`` 并在 ``route_handler`` 函数内部注册它。

.. caution:: 尽管 Litestar 暴露了 :meth:`register <.router.Router.register>` 方法，但不应滥用它。
    动态路由注册会增加应用的复杂性，使代码更难推理。
    因此应仅在绝对需要时使用。

:class:`路由器 <.router.Router>`
---------------------------------

:class:`路由器 <.router.Router>` 是 :class:`~.router.Router` 类的实例，
它是 :class:`Litestar 应用 <.app.Litestar>` 本身的基类。

一个 :class:`~.router.Router` 可以注册 :class:`控制器 <.controller.Controller>`、
:class:`路由处理器 <.handlers.BaseRouteHandler>` 函数和其他路由器，类似于 Litestar 构造函数：

.. code-block:: python
    :caption: 注册一个 :class:`~.router.Router`

    from litestar import Litestar, Router, get


    @get("/{order_id:int}")
    def order_handler(order_id: int) -> None: ...


    order_router = Router(path="/orders", route_handlers=[order_handler])
    base_router = Router(path="/base", route_handlers=[order_router])
    app = Litestar(route_handlers=[base_router])

一旦 ``order_router`` 在 ``base_router`` 上注册，``order_router`` 上注册的处理器函数将在
``/base/orders/{order_id}`` 上可用。

:class:`控制器 <.controller.Controller>`
------------------------------------------

:class:`控制器 <.controller.Controller>` 是 :class:`Controller <.controller.Controller>` 类的子类。
它们用于在特定子路径（即控制器的路径）下组织端点。
其目的是允许用户利用 Python 面向对象编程来更好地组织代码，并按逻辑关注点组织代码。

.. dropdown:: 点击查看注册控制器的示例

    .. code-block:: python
        :caption: 注册一个 :class:`~.controller.Controller`

        from litestar.plugins.pydantic import PydanticDTO
        from litestar.controller import Controller
        from litestar.dto import DTOConfig, DTOData
        from litestar.handlers import get, post, patch, delete
        from pydantic import BaseModel, UUID4


        class UserOrder(BaseModel):
           user_id: int
           order: str


        class PartialUserOrderDTO(PydanticDTO[UserOrder]):
           config = DTOConfig(partial=True)


        class UserOrderController(Controller):
           path = "/user-order"

           @post()
           async def create_user_order(self, data: UserOrder) -> UserOrder: ...

           @get(path="/{order_id:uuid}")
           async def retrieve_user_order(self, order_id: UUID4) -> UserOrder: ...

           @patch(path="/{order_id:uuid}", dto=PartialUserOrderDTO)
           async def update_user_order(
               self, order_id: UUID4, data: DTOData[PartialUserOrderDTO]
           ) -> UserOrder: ...

           @delete(path="/{order_id:uuid}")
           async def delete_user_order(self, order_id: UUID4) -> None: ...

上面是一个名为 ``UserOrder`` 模型的简单"CRUD"控制器示例。您可以在控制器上放置任意数量的
:doc:`路由处理器方法 </usage/routing/handlers>`，只要路径+HTTP 方法的组合是唯一的。

在 :class:`控制器 <.controller.Controller>` 上定义的 ``path`` 会被添加到在其上声明的路由处理器
定义的路径之前。因此，在上面的示例中，``create_user_order`` 具有 :class:`控制器 <.controller.Controller>`
的路径 - ``/user-order/``，而 ``retrieve_user_order`` 具有路径 ``/user-order/{order_id:uuid}``。

.. note:: 如果您不在控制器上声明 ``path`` 类变量，它将默认为根路径 ``"/"``。

多次注册组件
------------

您可以多次注册独立的路由处理器函数和控制器。

控制器
^^^^^^

.. code-block:: python
    :caption: 多次注册控制器

    from litestar import Router, Controller, get


    class MyController(Controller):
       path = "/controller"

       @get()
       def handler(self) -> None: ...


    internal_router = Router(path="/internal", route_handlers=[MyController])
    partner_router = Router(path="/partner", route_handlers=[MyController])
    consumer_router = Router(path="/consumer", route_handlers=[MyController])

在上面的示例中，同一个 ``MyController`` 类已在三个不同的路由器上注册。这是可能的，因为
传递给 :class:`路由器 <.router.Router>` 的不是类实例，而是类本身。
:class:`路由器 <.router.Router>` 创建自己的 :class:`控制器 <.controller.Controller>` 实例，
这确保了封装。

因此，在上面的示例中，将创建三个不同的 ``MyController`` 实例，每个实例挂载在不同的子路径上，
例如 ``/internal/controller``、``/partner/controller`` 和 ``/consumer/controller``。

路由处理器
^^^^^^^^^^

您也可以多次注册独立的路由处理器：

.. code-block:: python
    :caption: 多次注册路由处理器

    from litestar import Litestar, Router, get


    @get(path="/handler")
    def my_route_handler() -> None: ...


    internal_router = Router(path="/internal", route_handlers=[my_route_handler])
    partner_router = Router(path="/partner", route_handlers=[my_route_handler])
    consumer_router = Router(path="/consumer", route_handlers=[my_route_handler])

    Litestar(route_handlers=[internal_router, partner_router, consumer_router])

当处理器函数被注册时，它实际上被复制了。因此，每个路由器都有自己唯一的路由处理器实例。
路径行为与上面的控制器相同，即路由处理器函数将在以下路径中可访问：
``/internal/handler``、``/partner/handler`` 和 ``/consumer/handler``。

.. attention:: 您可以根据需要嵌套路由器 - 但要注意，一旦路由器被注册，就不能重新注册，否则会引发异常。

挂载 ASGI 应用
--------------

Litestar 支持在子路径上"挂载" ASGI 应用，即指定一个处理器函数来处理所有发送到给定路径的请求。

.. dropdown:: 点击查看挂载 ASGI 应用的示例

    .. literalinclude:: /examples/routing/mount_custom_app.py
        :language: python
        :caption: 挂载 ASGI 应用

处理器函数将接收所有以 ``/some/sub-path`` 开头的 URL 请求，例如 ``/some/sub-path``、
``/some/sub-path/abc``、``/some/sub-path/123/another/sub-path`` 等。

.. admonition:: 技术细节
    :class: info

    如果我们向上面的应用发送一个 URL 为 ``/some/sub-path`` 的请求，处理器将被调用，
    ``scope["path"]`` 的值将等于 ``"/"``。如果我们发送一个请求到 ``/some/sub-path/abc``，
    它也会被调用，``scope["path"]`` 将等于 ``"/abc"``。

当您需要组合其他 ASGI 应用的组件时，挂载特别有用 - 例如，用于第三方库。
以下示例在原理上与上面相同，但它使用 `Starlette <https://www.starlette.io/>`_：

.. dropdown:: 点击查看挂载 Starlette 应用的示例

    .. literalinclude:: /examples/routing/mounting_starlette_app.py
       :language: python
       :caption: 挂载 Starlette 应用

.. admonition:: 为什么 Litestar 使用基于 radix 的路由

    流行框架（如 Starlette、FastAPI 或 Flask）使用的正则表达式匹配非常擅长快速解析路径参数，
    当 URL 有大量路径参数时具有优势 - 我们可以将其视为 ``垂直`` 扩展。另一方面，它不擅长水平扩展 -
    路由越多，性能就越低。因此，这种方法的性能与应用大小之间存在反比关系，非常有利于小型微服务。
    Litestar 使用的基于 **trie** 的方法与应用的路由数量无关，使其具有更好的水平扩展特性，
    但代价是路径参数的解析速度稍慢。

    Litestar 实现了基于 `radix 树 <https://en.wikipedia.org/wiki/Radix_tree>`_ 或 *trie* 概念的路由解决方案。

    .. seealso:: 如果您对实现的技术方面感兴趣，请参阅
       `此 GitHub issue <https://github.com/litestar-org/litestar/issues/177>`_ -
       它包含对相关代码的深入讨论。
