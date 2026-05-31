==================================
实现自定义身份验证
==================================

Litestar 导出了 :class:`~.middleware.authentication.AbstractAuthenticationMiddleware`，
这是一个实现了 :class:`~.middleware.base.MiddlewareProtocol` 的 :term:`抽象基类 <abstract base class>`（ABC）。
要使用此类作为基础为您的应用添加身份验证，请子类化它并实现抽象方法
:meth:`~.middleware.authentication.AbstractAuthenticationMiddleware.authenticate_request`：

.. code-block:: python
    :caption: 通过子类化 :class:`~.middleware.authentication.AbstractAuthenticationMiddleware` 为您的应用添加身份验证

    from litestar.middleware import (
       AbstractAuthenticationMiddleware,
       AuthenticationResult,
    )
    from litestar.connection import ASGIConnection


    class MyAuthenticationMiddleware(AbstractAuthenticationMiddleware):
       async def authenticate_request(
           self, connection: ASGIConnection
       ) -> AuthenticationResult:
           # 在这里做一些事情。
           ...

如您所见，``authenticate_request`` 是一个异步函数，它接收一个连接实例，并应该返回一个
:class:`~.middleware.authentication.AuthenticationResult` 实例，它是一个
:doc:`dataclass <python:library/dataclasses>`，有两个属性：

1. ``user``：表示用户的非可选值。它被类型化为 ``Any``，因此它接收任何值，包括 ``None``。
2. ``auth``：表示身份验证方案的可选值。默认为 ``None``。

这些值然后作为 ``scope`` 字典的一部分设置，并分别作为
:attr:`Request.user <.connection.ASGIConnection.user>` 和
:attr:`Request.auth <.connection.ASGIConnection.auth>` 可用于 HTTP 路由处理器，
以及 :attr:`WebSocket.user <.connection.ASGIConnection.user>` 和
:attr:`WebSocket.auth <.connection.ASGIConnection.auth>` 可用于 websocket 路由处理器。

创建自定义身份验证中间件
------------------------

由于上述内容在抽象层面上很难理解，让我们看一个例子。

我们首先创建一个用户模型。它可以使用 msgspec、Pydantic、ODM、ORM 等实现。
为了这个示例，让我们假设它是一个 dataclass：

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 19-26
    :language: python
    :caption: 用户和令牌模型


我们现在可以创建我们的身份验证中间件：

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines:  29-43
    :language: python
    :caption: authentication_middleware.py


最后，我们需要将中间件传递给 Litestar 构造函数：


.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 80-88
    :language: python
    :caption: main.py


就是这样。``CustomAuthenticationMiddleware`` 现在将为每个请求运行，我们可以在 http 路由处理器中以以下方式访问这些：

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 46-51
    :language: python
    :caption: 使用 ``CustomAuthenticationMiddleware`` 在 http 路由处理器中访问用户和认证信息

或者对于 websocket 路由：

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 54-59
    :language: python
    :caption: 使用 ``CustomAuthenticationMiddleware`` 在 websocket 路由处理器中访问用户和认证信息


如果您想要在配置的路由之外排除单个路由：


.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 62-70
    :language: python
    :caption: 从 ``CustomAuthenticationMiddleware`` 中排除单个路由

当然，也可以对依赖项使用相同类型的机制：

.. literalinclude:: /examples/security/using_abstract_authentication_middleware.py
    :lines: 73-77
    :language: python
    :caption: 在依赖项中使用 ``CustomAuthenticationMiddleware``
