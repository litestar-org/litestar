======
守卫
======

守卫是 :term:`可调用对象 <python:callable>`，它们接收两个参数 - ``connection``，
它是 :class:`Request <.connection.Request>` 或 :class:`WebSocket <.connection.WebSocket>` 实例
（都是 :class:`~.connection.ASGIConnection` 的子类），以及 ``route_handler``，
它是 :class:`~.handlers.BaseRouteHandler` 的副本。它们的作用是通过验证连接是否被允许访问相关的端点处理器
来 *授权* 请求。如果验证失败，守卫应该引发 :exc:`HTTPException`，通常是带有 ``status_code`` 为 ``401``
的 :class:`~.exceptions.NotAuthorizedException`。

为了说明这一点，我们将在 Litestar 应用中实现一个基本的基于角色的授权系统。正如我们对 ``authentication``
所做的那样，我们将假设我们添加了某种持久层，而不在示例中实际指定它。

我们首先创建一个具有两个角色的 :class:`~enum.Enum` - ``consumer`` 和 ``admin``：

.. literalinclude:: /examples/security/guards.py
    :language: python
    :lines: 12-14
    :caption: 定义枚举 ``UserRole``

我们的 ``User`` 模型现在看起来像这样：

.. literalinclude:: /examples/security/guards.py
        :language: python
        :lines: 17-24
        :caption: 基于角色授权的用户模型

鉴于 ``User`` 模型有一个 ``role`` 属性，我们可以使用它来授权请求。
让我们创建一个只允许管理员用户访问某些路由处理器的守卫，然后将其添加到路由处理器函数：

.. literalinclude:: /examples/security/guards.py
        :language: python
        :lines: 27-29, 32-33
        :caption: 定义用于授权某些路由处理器的守卫 ``admin_user_guard``

在这里，``admin_user_guard`` 守卫检查用户是否是管理员。

由于 JWT 中间件，连接附加了一个 `user` 对象，请参阅 :doc:`authentication </usage/security/jwt>`，
特别是 :meth:`JWTAuth.retrieve_user_handler` 方法。

因此，只有管理员用户才能向 ``create_user`` 处理器发送 post 请求。

守卫作用域
----------

守卫是 Litestar :ref:`分层架构 <usage/applications:layered architecture>` 的一部分，
可以在应用的所有层上声明 - Litestar 实例、路由器、控制器和单个路由处理器：

.. literalinclude:: /examples/security/guards.py
    :language: python
    :lines: 36-49
    :caption: 在应用的不同层上声明守卫

守卫在 Litestar 应用中的位置取决于所需的访问控制范围和级别：

- 限制应该应用于单个路由处理器吗？
- 访问控制是针对控制器内的所有操作吗？
- 您是否想要保护特定路由器管理的所有路由？
- 或者您需要在整个应用中实施访问控制？

如您在上面的示例中所看到的 - ``guards`` 是一个 :class:`list`。这意味着您可以在每一层添加 **多个** 守卫。
与 :doc:`依赖项 </usage/dependency-injection>` 不同，守卫不会相互覆盖，而是 *累积* 的。
这意味着您可以在应用的不同层定义守卫，它们将组合在一起。

.. caution::

    如果守卫放置在控制器或应用级别，它们 **将** 在所有 ``OPTIONS`` 请求上执行。
    有关更多详细信息，包括解决方法，请参阅 https://github.com/litestar-org/litestar/issues/2314。


路由处理器的"opt"键
--------------------

有时可能需要在路由处理器本身上设置一些值 - 这些可以是权限或其他标志。
这可以通过路由处理器的 :ref:`opts kwarg <handler_opts>` 来实现

为了说明这一点，假设我们想要一个由"secret"令牌守护的端点，为此我们创建以下守卫：

.. literalinclude:: /examples/security/guards.py
    :language: python
    :lines: 52-61
