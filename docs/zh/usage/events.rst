事件
======

Litestar 支持事件发射器/监听器模式的简单实现：

.. code-block:: python

    from dataclasses import dataclass

    from litestar import Request, post
    from litestar.events import listener
    from litestar import Litestar

    from db import user_repository
    from utils.email import send_welcome_mail


    @listener("user_created")
    async def send_welcome_email_handler(email: str) -> None:
        # 在这里做一些事情来发送电子邮件
        await send_welcome_mail(email)


    @dataclass
    class CreateUserDTO:
        first_name: str
        last_name: str
        email: str


    @post("/users")
    async def create_user_handler(data: UserDTO, request: Request) -> None:
        # 在这里做一些事情来创建新用户
        # 例如，将用户插入数据库
        await user_repository.insert(data)

        # 假设我们现在已经插入了一个用户，我们想发送一封欢迎邮件。
        # 为了以非阻塞的方式做到这一点，我们将向监听器发出一个事件，该监听器将发送电子邮件，
        # 使用与我们返回响应的不同的异步块。
        request.app.emit("user_created", email=data.email)


    app = Litestar(
        route_handlers=[create_user_handler], listeners=[send_welcome_email_handler]
    )


上面的示例说明了这种模式的强大之处 - 它允许我们在不阻塞的情况下执行异步操作，并且不会减慢响应周期。

监听多个事件
++++++++++++++++++++++++++++

事件监听器可以监听多个事件：

.. code-block:: python

    from litestar.events import listener


    @listener("user_created", "password_changed")
    async def send_email_handler(email: str, message: str) -> None:
        # 在这里做一些事情来发送电子邮件

        await send_email(email, message)




使用多个监听器
++++++++++++++++++++++++

您还可以使用多个监听器监听相同的事件：

.. code-block:: python

    from uuid import UUID
    from dataclasses import dataclass

    from litestar import Request, post
    from litestar.events import listener

    from db import user_repository
    from utils.client import client
    from utils.email import send_farewell_email


    @listener("user_deleted")
    async def send_farewell_email_handler(email: str, **kwargs) -> None:
        # 在这里做一些事情来发送电子邮件
        await send_farewell_email(email)


    @listener("user_deleted")
    async def notify_customer_support(reason: str, **kwargs) -> None:
        # 在这里做一些事情来发送电子邮件
        await client.post("some-url", reason)


    @dataclass
    class DeleteUserDTO:
        email: str
        reason: str


    @post("/users")
    async def delete_user_handler(data: UserDTO, request: Request) -> None:
        await user_repository.delete({"email": email})
        request.app.emit("user_deleted", email=data.email, reason="deleted")



在上面的示例中，我们为同一事件执行了两个副作用，一个向用户发送电子邮件，另一个向服务管理系统发送 HTTP 请求以创建问题。

向监听器传递参数
++++++++++++++++++++++++++++++

方法 :meth:`emit <litestar.events.BaseEventEmitterBackend.emit>` 具有以下签名：

.. code-block:: python

    def emit(self, event_id: str, *args: Any, **kwargs: Any) -> None: ...



这意味着它期望一个 ``event_id`` 字符串，后跟任意数量的位置参数和关键字参数。虽然这非常灵活，但也意味着您需要确保给定事件的监听器可以处理所有预期的 args 和 kwargs。

例如，以下代码在 Python 中会引发异常：

.. code-block:: python

    @listener("user_deleted")
    async def send_farewell_email_handler(email: str) -> None:
        await send_farewell_email(email)


    @listener("user_deleted")
    async def notify_customer_support(reason: str) -> None:
        # 在这里做一些事情来发送电子邮件
        await client.post("some-url", reason)


    @dataclass
    class DeleteUserDTO:
        email: str
        reason: str


    @post("/users")
    async def delete_user_handler(data: UserDTO, request: Request) -> None:
        await user_repository.delete({"email": email})
        request.app.emit("user_deleted", email=data.email, reason="deleted")



这是因为两个监听器都将接收两个 kwargs - ``email`` 和 ``reason``。为了避免这种情况，前面的示例在两者中都有 ``**kwargs``：

.. code-block:: python

    @listener("user_deleted")
    async def send_farewell_email_handler(email: str, **kwargs) -> None:
        await send_farewell_email(email)


    @listener("user_deleted")
    async def notify_customer_support(reason: str, **kwargs) -> None:
        await client.post("some-url", reason)



创建事件发射器
-----------------------

"事件发射器"是一个继承自 :class:`BaseEventEmitterBackend <litestar.events.BaseEventEmitterBackend>` 的类，它本身继承自 :obj:`contextlib.AbstractAsyncContextManager`。

- :meth:`emit <litestar.events.BaseEventEmitterBackend.emit>`：这是执行实际发射逻辑的方法。

此外，必须实现 :obj:`contextlib.AbstractAsyncContextManager` 的抽象 ``__aenter__`` 和 ``__aexit__`` 方法，允许发射器用作异步上下文管理器。

默认情况下，Litestar 使用 :class:`SimpleEventEmitter <litestar.events.SimpleEventEmitter>`，它提供内存中的异步队列。

如果系统不需要依赖复杂的行为，例如重试机制、持久性或调度/cron，则此解决方案效果很好。对于这些更复杂的用例，用户应该使用支持事件的数据库/键值存储（Redis、Postgres 等）或消息代理、作业队列或任务队列技术来实现自己的后端。
