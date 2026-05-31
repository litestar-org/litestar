类型
=====

.. module:: litestar.types



可调用类型
--------------


.. autodata:: litestar.types.AfterExceptionHookHandler

.. autodata:: litestar.types.AfterRequestHookHandler

.. autodata:: litestar.types.AfterResponseHookHandler

.. autodata:: litestar.types.AnyCallable

.. autodata:: litestar.types.AsyncAnyCallable

.. autodata:: litestar.types.BeforeMessageSendHookHandler

.. autodata:: litestar.types.BeforeRequestHookHandler

.. autodata:: litestar.types.CacheKeyBuilder

.. autodata:: litestar.types.ExceptionHandler

.. autodata:: litestar.types.Guard

.. autodata:: litestar.types.LifespanHook

.. autodata:: litestar.types.OnAppInitHandler

.. autodata:: litestar.types.Serializer


ASGI 类型
----------

.. autodata:: litestar.types.Method

ASGI 应用程序
~~~~~~~~~~~~~~~~~

.. autodata:: litestar.types.ASGIApp

ASGI 应用程序参数
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autodata:: litestar.types.Scope

.. autodata:: litestar.types.Receive

.. autodata:: litestar.types.Send

ASGI 作用域
~~~~~~~~~~~~

.. autoclass:: litestar.types.ASGIVersion

.. autoclass:: litestar.types.BaseScope

.. autoclass:: litestar.types.HTTPScope

.. autoclass:: litestar.types.LifeSpanScope

.. autoclass:: litestar.types.WebSocketScope


ASGI 事件
~~~~~~~~~~~~

.. autoclass:: litestar.types.HTTPRequestEvent

.. autoclass:: litestar.types.HTTPResponseStartEvent

.. autoclass:: litestar.types.HTTPResponseBodyEvent

.. autoclass:: litestar.types.HTTPServerPushEvent

.. autoclass:: litestar.types.HTTPDisconnectEvent

.. autoclass:: litestar.types.WebSocketConnectEvent

.. autoclass:: litestar.types.WebSocketAcceptEvent

.. autoclass:: litestar.types.WebSocketReceiveEvent

.. autoclass:: litestar.types.WebSocketSendEvent

.. autoclass:: litestar.types.WebSocketResponseStartEvent

.. autoclass:: litestar.types.WebSocketResponseBodyEvent

.. autoclass:: litestar.types.WebSocketDisconnectEvent

.. autoclass:: litestar.types.WebSocketCloseEvent

.. autoclass:: litestar.types.LifeSpanStartupEvent

.. autoclass:: litestar.types.LifeSpanShutdownEvent

.. autoclass:: litestar.types.LifeSpanStartupCompleteEvent

.. autoclass:: litestar.types.LifeSpanStartupFailedEvent

.. autoclass:: litestar.types.LifeSpanShutdownCompleteEvent

.. autoclass:: litestar.types.LifeSpanShutdownFailedEvent


事件分组
~~~~~~~~~~~~~~~

.. autodata:: litestar.types.HTTPReceiveMessage

.. autodata:: litestar.types.WebSocketReceiveMessage

.. autodata:: litestar.types.LifeSpanReceiveMessage

.. autodata:: litestar.types.HTTPSendMessage

.. autodata:: litestar.types.WebSocketSendMessage

.. autodata:: litestar.types.LifeSpanSendMessage

.. autodata:: litestar.types.LifeSpanReceive

.. autodata:: litestar.types.LifeSpanSend

发送/接收参数类型
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autodata:: litestar.types.Message

.. autodata:: litestar.types.ReceiveMessage


辅助类型
------------

辅助类型是可以使用的有用的泛型类型。

.. autoclass:: litestar.types.SyncOrAsyncUnion

.. autoclass:: litestar.types.AnyIOBackend

.. autoclass:: litestar.types.OptionalSequence


协议
---------

.. autoclass:: litestar.types.Logger


复合类型
---------------

.. autoclass:: litestar.types.Dependencies

.. autoclass:: litestar.types.ExceptionHandlersMap

.. autodata:: litestar.types.Middleware

.. autoclass:: litestar.types.ResponseCookies

.. autoclass:: litestar.types.ResponseHeaders

.. autoclass:: litestar.types.PathType

.. autodata:: litestar.types.Scopes

.. autoclass:: litestar.types.TypeEncodersMap

.. autoclass:: litestar.types.TypeDecodersSequence

.. autoclass:: litestar.types.ParametersMap
