===================
创建中间件
===================

如 :ref:`使用中间件 <using-middleware>` 中所述，Litestar 中的中间件是 **任何可调用对象**，
它接受一个名为 ``app`` 的 kwarg（即下一个 ASGI 处理器，即 :class:`~litestar.types.ASGIApp`），
并返回一个 ``ASGIApp``。

之前给出的示例使用的是工厂函数，即：

.. code-block:: python

   from litestar.types import ASGIApp, Scope, Receive, Send


   def middleware_factory(app: ASGIApp) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # 在这里做一些事情
           ...
           await app(scope, receive, send)

       return my_middleware


扩展 ``ASGIMiddleware``
------------------------

虽然使用函数是一种完全可行的方法，但推荐的方式是使用 :class:`~litestar.middleware.ASGIMiddleware` 抽象基类，
它还包括根据 ASGI ``scope["type"]``、处理器 ``opt`` 键或路径模式动态跳过中间件的功能，
以及向中间件传递配置的简单方法；它不实现 ``__init__`` 方法，因此子类可以自由使用它来自定义中间件的配置。


修改请求和响应
++++++++++++++

中间件不仅可以用于在其他 ASGI 可调用对象 *周围* 执行，它们还可以通过"包装"各自的 ``receive`` 和 ``send``
ASGI 可调用对象来拦截和修改请求/响应周期中的传入和传出数据。

以下演示如何向所有传出响应添加带有时间戳的请求计时头：

.. literalinclude:: /examples/middleware/request_timing.py
    :language: python


配置约束
++++++++

虽然保持中间件彼此解耦是一种良好实践，但有时由于中间件提供的功能的性质，隐式耦合是不可避免的。

例如，缓存中间件和身份验证中间件可能会根据它们应用的顺序产生非常不同的结果；
假设一个不考虑身份验证状态的简单缓存中间件，如果它在身份验证中间件 *之前* 应用，
它可能会缓存已验证的响应并将其提供给下一个未验证的请求。

特别是当应用程序变得更大更复杂时，跟踪所有这些隐式耦合和依赖关系可能会变得困难，
或者如果中间件在单独的包中实现并且不知道它是如何被应用的，则完全不可能。

为了帮助解决这个问题，:class:`~litestar.middleware.ASGIMiddleware` 允许指定一组
:class:`~litestar.middleware.constraints.MiddlewareConstraints` - 一旦配置，
这些将在应用程序启动时进行验证。

使用约束，上面给出的示例可能会这样解决：

.. literalinclude:: /examples/middleware/constraints.py
    :language: python

在这里，我们指定 ``CachingMiddleware`` 的每个实例都必须在
:class:`~litestar.middleware.authentication.AbstractAuthenticationMiddleware` 的任何实例之后。


.. tip::

    在引用类时，约束始终适用于该类型的所有实例和子类


前向引用
~~~~~~~~

引用其他中间件的约束可以使用字符串作为前向引用，以处理循环导入或来自可能不可用的包的中间件等情况：

.. literalinclude:: /examples/middleware/constraints_string_ref.py
    :language: python

此前向引用将尝试从 ``some_package.some_module`` 导入 ``SomeMiddleware``。
使用 ``ignore_import_error=True``，如果导入不成功，约束将被忽略。


中间件顺序
~~~~~~~~~~

对于顺序约束（``before``、``after``、``first``、``last``），重要的是要注意顺序是根据与位置的接近程度定义的。
实际上，这意味着设置 ``first=True`` 的中间件必须是 *第一* 层（即应用程序）上的 *第一个* 中间件，
而设置 ``last=True`` 的中间件必须是 *最后* 层（即路由处理器）上的 *最后一个* 中间件。

.. code-block:: python

    @get("/", middleware=[FifthMiddleware, SixthMiddleware])
    async def handler() -> None:
        pass

    router = Router(
        "/",
        [handler],
        middleware=[
            ThirdMiddleware(),
            FourthMiddleware()
        ]
    )

    app = Litestar(
        middleware=[
            FirstMiddleware(),
            SecondMiddleware()
        ]
    )

约束和插件
~~~~~~~~~~

使用添加中间件的插件时，重要的是要理解这些中间件是在应用程序上定义的中间件 *之后* 
和在其他层上定义的中间件 *之前* 添加的。

但是，约束是在添加所有中间件后进行评估的，因此插件添加的中间件上的顺序约束必须考虑它被添加到的位置。

大多数时候在插件中你会做 ``app_config.middleware.append(MyCustomMiddleware)``，
如果它没有附加约束，这将是可以的。

现在假设 ``MyCustomMiddleware`` 有约束 ``first=True``，那么添加它的正确方法是
``app_config.middleware.insert(0, MyCustomMiddleware())``，以便它是堆栈中的第一个中间件。


从 ``MiddlewareProtocol`` / ``AbstractMiddleware`` 迁移
+++++++++++++++++++++++++++++++++++++++++++++++++++++++++

:class:`~litestar.middleware.ASGIMiddleware` 在 Litestar 2.15 中引入。
如果您之前一直使用 ``MiddlewareProtocol`` / ``AbstractMiddleware`` 来实现中间件，
有一个简单的迁移路径可以使用 ``ASGIMiddleware``。

**从 MiddlewareProtocol**

.. tab-set::

    .. tab-item:: MiddlewareProtocol

        .. literalinclude:: /examples/middleware/middleware_protocol_migration_old.py
            :language: python

    .. tab-item:: ASGIMiddleware

        .. literalinclude:: /examples/middleware/middleware_protocol_migration_new.py
            :language: python



**从 AbstractMiddleware**

.. tab-set::

    .. tab-item:: MiddlewareProtocol

        .. literalinclude:: /examples/middleware/abstract_middleware_migration_old.py
            :language: python

    .. tab-item:: ASGIMiddleware

        .. literalinclude:: /examples/middleware/abstract_middleware_migration_new.py
            :language: python






使用 MiddlewareProtocol
------------------------

:class:`~litestar.middleware.base.MiddlewareProtocol` 类是一个
`PEP 544 Protocol <https://peps.python.org/pep-0544/>`_，它指定了中间件的最小实现如下：

.. code-block:: python

   from typing import Protocol, Any
   from litestar.types import ASGIApp, Scope, Receive, Send


   class MiddlewareProtocol(Protocol):
       def __init__(self, app: ASGIApp, **kwargs: Any) -> None: ...

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None: ...

``__init__`` 方法接收并设置"app"。*重要的是要理解* 在这种情况下，app 不是 Litestar 的实例，
而是堆栈中的下一个中间件，它也是一个 ASGI 应用。

``__call__`` 方法使这个类成为一个 ``callable``，即一旦实例化，这个类就像一个函数，
它具有 ASGI 应用的签名：三个参数 ``scope, receive, send`` 由
`ASGI 规范 <https://asgi.readthedocs.io/en/latest/index.html>`_ 指定，
它们的值来自用于运行 Litestar 的 ASGI 服务器（例如 ``uvicorn``）。

要将此协议用作基础，只需像继承任何其他类一样继承它，并实现它指定的两个方法：

.. code-block:: python

   import logging

   from litestar.types import ASGIApp, Receive, Scope, Send
   from litestar import Request
   from litestar.middleware.base import MiddlewareProtocol

   logger = logging.getLogger(__name__)


   class MyRequestLoggingMiddleware(MiddlewareProtocol):
       def __init__(self, app: ASGIApp) -> None:  # 也可以有其他参数
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if scope["type"] == "http":
               request = Request(scope)
               logger.info("Got request: %s - %s", request.method, request.url)
           await self.app(scope, receive, send)

.. important::

    虽然 ``scope`` 用于通过将其传递给 :class:`~litestar.connection.Request` 构造函数来创建请求实例，
    这使得访问更简单，因为它已经为您进行了一些解析，但实际的真实来源仍然是 ``scope`` - 而不是请求。
    如果您需要修改请求的数据，您必须修改 scope 对象，而不是像上面那样创建的任何临时请求对象。


使用 MiddlewareProtocol 响应
+++++++++++++++++++++++++++++

一旦中间件完成了它正在做的任何事情，它应该将 ``scope``、``receive`` 和 ``send`` 传递给 ASGI 应用
并 await 它。这就是上面示例中的 ``await self.app(scope, receive, send)`` 所做的。
让我们探讨另一个示例 - 从中间件重定向请求到不同的 url：

.. code-block:: python

   from litestar.types import ASGIApp, Receive, Scope, Send

   from litestar.response.redirect import ASGIRedirectResponse
   from litestar import Request
   from litestar.middleware.base import MiddlewareProtocol


   class RedirectMiddleware(MiddlewareProtocol):
       def __init__(self, app: ASGIApp) -> None:
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if Request(scope).session is None:
               response = ASGIRedirectResponse(path="/login")
               await response(scope, receive, send)
           else:
               await self.app(scope, receive, send)

如您在上面所看到的，给定某个条件（``request.session`` 为 ``None``），
我们创建一个 :class:`~litestar.response.redirect.ASGIRedirectResponse` 然后 await 它。
否则，我们 await ``self.app``

使用 MiddlewareProtocol 修改 ASGI 请求和响应
++++++++++++++++++++++++++++++++++++++++++++++

.. important::

    如果您想在为路由处理器函数创建 :class:`~litestar.response.Response` 对象之后
    但在传输实际响应消息之前修改它，正确的位置是使用名为 :ref:`after_request <after_request>` 的特殊生命周期钩子。
    本节中的说明是关于如何修改 ASGI 响应消息本身，这是响应过程中的更进一步的步骤。

使用 :class:`~litestar.middleware.base.MiddlewareProtocol`，您可以通过"包装"相应的 ``receive`` 和 ``send``
ASGI 函数来拦截和修改请求/响应周期中的传入和传出数据。

为了演示这一点，假设我们想要向所有传出响应附加一个带有时间戳的头。我们可以通过执行以下操作来实现：

.. code-block:: python

   import time

   from litestar.datastructures import MutableScopeHeaders
   from litestar.types import Message, Receive, Scope, Send
   from litestar.middleware.base import MiddlewareProtocol
   from litestar.types import ASGIApp


   class ProcessTimeHeader(MiddlewareProtocol):
       def __init__(self, app: ASGIApp) -> None:
           super().__init__(app)
           self.app = app

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           if scope["type"] == "http":
               start_time = time.monotonic()

               async def send_wrapper(message: Message) -> None:
                   if message["type"] == "http.response.start":
                       process_time = time.monotonic() - start_time
                       headers = MutableScopeHeaders.from_message(message=message)
                       headers["X-Process-Time"] = str(process_time)
                   await send(message)

               await self.app(scope, receive, send_wrapper)
           else:
               await self.app(scope, receive, send)

继承 AbstractMiddleware
------------------------

Litestar 提供了一个 :class:`~litestar.middleware.base.AbstractMiddleware` 类，可以扩展以创建中间件：

.. code-block:: python

   import time

   from litestar.enums import ScopeType
   from litestar.middleware import AbstractMiddleware
   from litestar.datastructures import MutableScopeHeaders
   from litestar.types import Message, Receive, Scope, Send


   class MyMiddleware(AbstractMiddleware):
       scopes = {ScopeType.HTTP}
       exclude = ["first_path", "second_path"]
       exclude_opt_key = "exclude_from_middleware"

       async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
           start_time = time.monotonic()

           async def send_wrapper(message: "Message") -> None:
               if message["type"] == "http.response.start":
                   process_time = time.monotonic() - start_time
                   headers = MutableScopeHeaders.from_message(message=message)
                   headers["X-Process-Time"] = str(process_time)
               await send(message)

           await self.app(scope, receive, send_wrapper)

上面示例中定义的三个类变量 ``scopes``、``exclude`` 和 ``exclude_opt_key`` 可用于微调中间件被调用的路由和请求类型：


- scopes 变量是一个集合，可以包括以下任一或两者：``ScopeType.HTTP`` 和 ``ScopeType.WEBSOCKET``，默认为两者都有。
- ``exclude`` 接受单个字符串或字符串列表，它们被编译成正则表达式，用于检查请求的 ``path``。
- ``exclude_opt_key`` 是在路由处理器的 :class:`Router.opt <litestar.router.Router>` 字典中使用的键，用于布尔值，是否从中间件中省略。

因此，在以下示例中，中间件仅针对名为 ``not_excluded_handler`` 的处理器在 ``/greet`` 路由上运行：

.. literalinclude:: /examples/middleware/base.py
    :language: python

.. danger::

    使用 ``/`` 作为排除模式将禁用此中间件用于所有路由，因为作为正则表达式，它匹配 *每个* 路径


使用 DefineMiddleware 传递参数
-------------------------------

Litestar 提供了一种简单的方法，使用 :class:`~litestar.middleware.base.DefineMiddleware` 类
向中间件传递位置参数（``*args``）和关键字参数（``**kwargs``）。让我们扩展上面示例中使用的工厂函数以接受一些
args 和 kwargs，然后使用 ``DefineMiddleware`` 将这些值传递给我们的中间件：

.. code-block:: python

   from litestar.types import ASGIApp, Scope, Receive, Send
   from litestar import Litestar
   from litestar.middleware import DefineMiddleware


   def middleware_factory(my_arg: int, *, app: ASGIApp, my_kwarg: str) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # 在这里我们可以为某些目的使用 my_arg 和 my_kwarg
           ...
           await app(scope, receive, send)

       return my_middleware


   app = Litestar(
       route_handlers=[...],
       middleware=[DefineMiddleware(middleware_factory, 1, my_kwarg="abc")],
   )

``DefineMiddleware`` 是一个简单的容器 - 它将中间件可调用对象作为第一个参数，然后是任何位置参数，
后跟关键字参数。中间件可调用对象将使用这些值以及上面提到的 kwarg ``app`` 调用。
