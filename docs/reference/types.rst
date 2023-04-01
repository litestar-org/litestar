types
=====

.. py:currentmodule:: starlite.types



Callable types
--------------


.. autodata:: starlite.types.AfterExceptionHookHandler

.. autodata:: starlite.types.AfterRequestHookHandler

.. autodata:: starlite.types.AfterResponseHookHandler

.. autodata:: starlite.types.AnyCallable

.. autodata:: starlite.types.AsyncAnyCallable

.. autodata:: starlite.types.BeforeMessageSendHookHandler

.. autodata:: starlite.types.BeforeRequestHookHandler

.. autodata:: starlite.types.CacheKeyBuilder

.. autodata:: starlite.types.ExceptionHandler

.. autodata:: starlite.types.Guard

.. autodata:: starlite.types.LifeSpanHandler

.. autodata:: starlite.types.LifeSpanHookHandler

.. autodata:: starlite.types.OnAppInitHandler

.. autodata:: starlite.types.Serializer


ASGI Types
----------

.. autodata:: starlite.types.Method

ASGI Application
~~~~~~~~~~~~~~~~~

.. autodata:: starlite.types.ASGIApp

ASGI Application Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autodata:: starlite.types.Scope

.. autodata:: starlite.types.Receive

.. autodata:: starlite.types.Send

ASGI Scopes
~~~~~~~~~~~~

.. autodata:: starlite.types.ASGIVersion

.. autodata:: starlite.types.BaseScope

.. autodata:: starlite.types.HTTPScope

.. autodata:: starlite.types.LifeSpanScope

.. autodata:: starlite.types.WebSocketScope


ASGI Events
~~~~~~~~~~~~

.. autoclass:: starlite.types.HTTPRequestEvent

.. autoclass:: starlite.types.HTTPResponseStartEvent

.. autoclass:: starlite.types.HTTPResponseBodyEvent

.. autoclass:: starlite.types.HTTPServerPushEvent

.. autoclass:: starlite.types.HTTPDisconnectEvent

.. autoclass:: starlite.types.WebSocketConnectEvent

.. autoclass:: starlite.types.WebSocketAcceptEvent

.. autoclass:: starlite.types.WebSocketReceiveEvent

.. autoclass:: starlite.types.WebSocketSendEvent

.. autoclass:: starlite.types.WebSocketResponseStartEvent

.. autoclass:: starlite.types.WebSocketResponseBodyEvent

.. autoclass:: starlite.types.WebSocketDisconnectEvent

.. autoclass:: starlite.types.WebSocketCloseEvent

.. autoclass:: starlite.types.LifeSpanStartupEvent

.. autoclass:: starlite.types.LifeSpanShutdownEvent

.. autoclass:: starlite.types.LifeSpanStartupCompleteEvent

.. autoclass:: starlite.types.LifeSpanStartupFailedEvent

.. autoclass:: starlite.types.LifeSpanShutdownCompleteEvent

.. autoclass:: starlite.types.LifeSpanShutdownFailedEvent


Event Groupings
~~~~~~~~~~~~~~~

.. autodata:: starlite.types.HTTPReceiveMessage

.. autodata:: starlite.types.WebSocketReceiveMessage

.. autodata:: starlite.types.LifeSpanReceiveMessage

.. autodata:: starlite.types.HTTPSendMessage

.. autodata:: starlite.types.WebSocketSendMessage

.. autodata:: starlite.types.LifeSpanSendMessage

.. autodata:: starlite.types.LifeSpanReceive

.. autodata:: starlite.types.LifeSpanSend

Send / Receive Parameter Types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

.. autodata:: starlite.types.Message

.. autodata:: starlite.types.ReceiveMessage


Helper Types
------------

Helper types are useful generic types that can be used.

.. autoclass:: starlite.types.SyncOrAsyncUnion

.. autoclass:: starlite.types.AnyIOBackend

.. autoclass:: starlite.types.OptionalSequence


Protocols
---------

.. autoclass:: starlite.types.Logger


Composite Types
---------------

.. autoclass:: starlite.types.Dependencies

.. autoclass:: starlite.types.ExceptionHandlersMap

.. autodata:: starlite.types.Middleware

.. autoclass:: starlite.types.ResponseCookies

.. autoclass:: starlite.types.ResponseHeaders

.. autoclass:: starlite.types.PathType

.. autodata:: starlite.types.Scopes

.. autoclass:: starlite.types.TypeEncodersMap

.. autoclass:: starlite.types.ParametersMap


File types
----------

.. autoclass:: starlite.types.FileInfo
    :members:


.. autoclass:: starlite.types.FileSystemProtocol
    :members:

Parsed signature types
----------------------

.. autoclass:: starlite.types.parsed_signature.ParsedSignature
    :members:

.. autoclass:: starlite.types.parsed_signature.ParsedParameter
    :members:

.. autoclass:: starlite.types.parsed_signature.ParsedAnnotation
    :members:
