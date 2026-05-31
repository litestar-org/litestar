.. _using-middleware:

================
使用中间件
================

Litestar 中的中间件是任何接收至少一个名为 ``app`` 的 kwarg 并返回
:class:`ASGIApp <litestar.types.ASGIApp>` 的可调用对象。``ASGIApp`` 只是一个异步函数，
它接收 ASGI 原语 ``scope``、``receive`` 和 ``send``，并调用下一个 ``ASGIApp`` 或返回响应 / 处理 websocket 连接。

例如，以下函数可以用作中间件，因为它接收 ``app`` kwarg 并返回 ``ASGIApp``：

.. code-block:: python

   from litestar.types import ASGIApp, Scope, Receive, Send


   def middleware_factory(app: ASGIApp) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # 在这里做一些事情
           ...
           await app(scope, receive, send)

       return my_middleware

然后我们可以将此中间件传递给 :class:`Litestar <.app.Litestar>` 实例，它将在每个请求上调用：

.. code-block:: python

   from litestar.types import ASGIApp, Scope, Receive, Send
   from litestar import Litestar


   def middleware_factory(app: ASGIApp) -> ASGIApp:
       async def my_middleware(scope: Scope, receive: Receive, send: Send) -> None:
           # 在这里做一些事情
           ...
           await app(scope, receive, send)

       return my_middleware


   app = Litestar(route_handlers=[...], middleware=[middleware_factory])

在上面的示例中，Litestar 将调用 ``middleware_factory`` 函数并将 ``app`` 传递给它。
重要的是要理解，这个 kwarg 不是指 Litestar 应用程序，而是堆栈中的下一个 ``ASGIApp``。
然后它将把返回的 ``my_middleware`` 函数插入到应用程序中每个路由的堆栈中 - 因为我们在应用程序级别声明了它。

.. admonition::  分层架构
    :class: seealso

    中间件是 Litestar 分层架构的一部分，这意味着您可以在应用程序的每一层上设置它们。

    您可以在这里阅读更多相关信息：:ref:`usage/applications:layered architecture`


中间件调用顺序
--------------

由于我们遍历应用层的方式，中间件堆栈是按"应用程序 > 处理器"的顺序构建的，
这是我们希望中间件被调用的顺序。

然而，使用此顺序，由于每个中间件包装下一个可调用对象，堆栈中的 *第一个* 中间件
将成为 *最内层* 的包装器，即最后一个接收请求并第一个看到响应的。

为了实现预期的调用顺序，我们以相反的顺序（"处理器 -> 应用程序"）执行包装。


.. mermaid::

    graph TD
        request --> M1
        M1 --> M2
        M2 --> H
        H --> M2R
        M2R --> M1R
        M1R --> response

        subgraph M1 [middleware_1]
            M2
            subgraph M2 [middleware_2]
                H[handler]
            end
        end

        style M1 stroke:#333,stroke-width:2px
        style M2 stroke:#555,stroke-width:1.5px
        style H stroke:#777,stroke-width:1px



.. literalinclude:: /examples/middleware/call_order.py
    :language: python



中间件和异常
------------

当路由处理器或 :doc:`依赖项 </usage/dependency-injection>` 引发异常时，
它将通过 :ref:`异常处理器 <usage/exceptions:exception handling>` 转换为响应。
此响应将遵循应用程序的正常"流程"，因此，中间件仍然应用于它。

与任何好的规则一样，也有例外。在这种情况下，它们是 Litestar 的 ASGI 路由器引发的两个异常：


* :class:`NotFoundException <litestar.exceptions.http_exceptions.NotFoundException>`
* :class:`MethodNotAllowedException <litestar.exceptions.http_exceptions.MethodNotAllowedException>`

它们在 **中间件堆栈被调用之前** 引发，只会由 ``Litestar`` 实例本身定义的异常处理器处理。
如果您希望修改从这些异常生成的错误响应，您将不得不使用应用程序层异常处理器。
