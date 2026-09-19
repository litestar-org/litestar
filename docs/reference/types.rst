types
=====

.. module:: litestar.types



Callable types
--------------


.. autotype:: litestar.types.AfterExceptionHookHandler

.. autotype:: litestar.types.AfterRequestHookHandler

.. autotype:: litestar.types.AfterResponseHookHandler

.. autotype:: litestar.types.AnyCallable

.. autotype:: litestar.types.AsyncAnyCallable

.. autotype:: litestar.types.BeforeMessageSendHookHandler

.. autotype:: litestar.types.BeforeRequestHookHandler

.. autotype:: litestar.types.CacheKeyBuilder

.. autotype:: litestar.types.ExceptionHandler

.. autotype:: litestar.types.Guard

.. autotype:: litestar.types.LifespanHook

.. autotype:: litestar.types.OnAppInitHandler

.. autotype:: litestar.types.Serializer


ASGI Types
----------

.. autotype:: litestar.types.asgi_types.HttpMethodName

.. autotype:: litestar.types.Method

ASGI Application
~~~~~~~~~~~~~~~~~

.. autotype:: litestar.types.ASGIApp

ASGI Application Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autotype:: litestar.types.Scope

.. autotype:: litestar.types.Receive

.. autotype:: litestar.types.Send

ASGI Scopes
~~~~~~~~~~~~

.. autoclass:: litestar.types.ASGIVersion

.. autoclass:: litestar.types.asgi_types.HeaderScope

.. autoclass:: litestar.types.BaseScope

.. autoclass:: litestar.types.HTTPScope

.. autoclass:: litestar.types.LifeSpanScope

.. autoclass:: litestar.types.WebSocketScope


ASGI Events
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


Event Groupings
~~~~~~~~~~~~~~~

.. autotype:: litestar.types.HTTPReceiveMessage

.. autotype:: litestar.types.WebSocketReceiveMessage

.. autotype:: litestar.types.LifeSpanReceiveMessage

.. autotype:: litestar.types.HTTPSendMessage

.. autotype:: litestar.types.WebSocketSendMessage

.. autotype:: litestar.types.LifeSpanSendMessage

.. autotype:: litestar.types.LifeSpanReceive

.. autotype:: litestar.types.LifeSpanSend

Send / Receive Parameter Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autotype:: litestar.types.Message

.. autotype:: litestar.types.ReceiveMessage


Helper Types
------------

Helper types are useful generic types that can be used.

.. autotype:: litestar.types.SyncOrAsyncUnion

.. autotype:: litestar.types.AnyIOBackend

.. autotype:: litestar.types.OptionalSequence

.. autoclass:: litestar.types.internal_types.PathParameterDefinition

Protocols
---------

.. autoclass:: litestar.types.Logger


Composite Types
---------------

.. autotype:: litestar.types.Dependencies

.. autotype:: litestar.types.ExceptionHandlersMap

.. autotype:: litestar.types.Middleware

.. autotype:: litestar.types.ResponseCookies

.. autotype:: litestar.types.ResponseHeaders

.. autotype:: litestar.types.PathType

.. autotype:: litestar.types.Scopes

.. autotype:: litestar.types.TypeEncodersMap

.. autotype:: litestar.types.TypeDecodersSequence

.. autotype:: litestar.types.ParametersMap

.. autotype:: litestar.types.callable_types.OperationIDCreator
