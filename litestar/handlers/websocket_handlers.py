from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from functools import partial
from typing import TYPE_CHECKING, Callable, Coroutine

from msgspec.json import Encoder as JsonEncoder

from litestar.exceptions import ImproperlyConfiguredException, WebSocketDisconnect
from litestar.handlers.base import BaseRouteHandler
from litestar.serialization import decode_json, default_serializer
from litestar.types.builtin_types import NoneType
from litestar.types.empty import Empty
from litestar.utils import AsyncCallable, is_async_callable
from litestar.utils.signature import ParsedSignature

__all__ = ("WebsocketRouteHandler", "websocket", "websocket_listener", "WebsocketListener")

if TYPE_CHECKING:
    from typing import Any, Mapping

    from litestar.connection import WebSocket
    from litestar.dto.interface import DTOInterface
    from litestar.types import (
        AnyCallable,
        Dependencies,
        EmptyType,
        ExceptionHandler,
        Guard,
        MaybePartial,  # noqa: F401
        Middleware,
        SyncOrAsyncUnion,
        TypeEncodersMap,
    )
    from litestar.types.asgi_types import WebSocketMode


class WebsocketRouteHandler(BaseRouteHandler["WebsocketRouteHandler"]):
    """Websocket route handler decorator.

    Use this decorator to decorate websocket handler functions.
    """

    __slots__ = ()

    def __init__(
        self,
        path: str | None | list[str] | None = None,
        *,
        dependencies: Dependencies | None = None,
        dto: type[DTOInterface] | None | EmptyType = Empty,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        guards: list[Guard] | None = None,
        middleware: list[Middleware] | None = None,
        name: str | None = None,
        opt: dict[str, Any] | None = None,
        return_dto: type[DTOInterface] | None | EmptyType = Empty,
        signature_namespace: Mapping[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ``WebsocketRouteHandler``

        Args:
            path: A path fragment for the route handler function or a sequence of path fragments. If not given defaults
                to ``/``
            dependencies: A string keyed mapping of dependency :class:`Provider <.di.Provide>` instances.
            dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for (de)serializing and
                validation of request data.
            exception_handlers: A mapping of status codes and/or exception types to handler functions.
            guards: A sequence of :class:`Guard <.types.Guard>` callables.
            middleware: A sequence of :class:`Middleware <.types.Middleware>`.
            name: A string identifying the route handler.
            opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
                wherever you have access to :class:`Request <.connection.Request>` or
                :class:`ASGI Scope <.types.Scope>`.
            return_dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for serializing
                outbound response data.
            signature_namespace: A mapping of names to types for use in forward reference resolution during signature modelling.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """

        super().__init__(
            path=path,
            dto=dto,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            middleware=middleware,
            name=name,
            opt=opt,
            return_dto=return_dto,
            signature_namespace=signature_namespace,
            **kwargs,
        )

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it's set by inspecting its return annotations."""
        super()._validate_handler_function()

        if not self.parsed_fn_signature.return_type.is_subclass_of(NoneType):
            raise ImproperlyConfiguredException("Websocket handler functions should return 'None'")
        if "socket" not in self.parsed_fn_signature.parameters:
            raise ImproperlyConfiguredException("Websocket handlers must set a 'socket' kwarg")
        for param in ("request", "body", "data"):
            if param in self.parsed_fn_signature.parameters:
                raise ImproperlyConfiguredException(f"The {param} kwarg is not supported with websocket handlers")
        if not is_async_callable(self.fn.value):
            raise ImproperlyConfiguredException("Functions decorated with 'websocket' must be async functions")


websocket = WebsocketRouteHandler


class websocket_listener(WebsocketRouteHandler):
    """A websocket listener that automatically accepts a connection, handles disconnects,
    invokes a callback function every time new data is received and sends any data
    returned
    """

    def __init__(
        self,
        path: str | None | list[str] | None = None,
        *,
        dependencies: Dependencies | None = None,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        guards: list[Guard] | None = None,
        middleware: list[Middleware] | None = None,
        receive_mode: WebSocketMode = "text",
        send_mode: WebSocketMode = "text",
        name: str | None = None,
        on_accept: Callable[[WebSocket], SyncOrAsyncUnion[None]] | None = None,
        on_disconnect: Callable[[WebSocket], SyncOrAsyncUnion[None]] | None = None,
        opt: dict[str, Any] | None = None,
        signature_namespace: Mapping[str, Any] | None = None,
        type_encoders: TypeEncodersMap | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ``WebsocketRouteHandler``

        Args:
            path: A path fragment for the route handler function or a sequence of path fragments. If not given defaults
                to ``/``
            dependencies: A string keyed mapping of dependency :class:`Provider <.di.Provide>` instances.
            exception_handlers: A mapping of status codes and/or exception types to handler functions.
            guards: A sequence of :class:`Guard <.types.Guard>` callables.
            middleware: A sequence of :class:`Middleware <.types.Middleware>`.
            receive_mode: Websocket mode to receive data in, either `text` or `binary`.
            send_mode: Websocket mode to receive data in, either `text` or `binary`.
            name: A string identifying the route handler.
            on_accept: Callback invoked after a connection has been accepted, receiving the
                :class:`WebSocket <.connection.WebSocket>` instance as its only argument
            on_disconnect: Callback invoked after a connection has been closed, receiving the
                :class:`WebSocket <.connection.WebSocket>` instance as its only argument
            opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
                wherever you have access to :class:`Request <.connection.Request>` or
                :class:`ASGI Scope <.types.Scope>`.
            signature_namespace: A mapping of names to types for use in forward reference resolution during signature
                modelling.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        self._receive_mode = receive_mode
        self._send_mode = send_mode
        self._on_accept = AsyncCallable(on_accept) if on_accept else None
        self._on_disconnect = AsyncCallable(on_disconnect) if on_disconnect else None
        self.type_encoders = type_encoders

        super().__init__(
            path=path,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            middleware=middleware,
            name=name,
            opt=opt,
            signature_namespace=signature_namespace,
            **kwargs,
        )

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it's set by inspecting its return annotations."""
        # since none of the validation rules of WebsocketRouteHandler apply here, this is let empty. Validation of the
        # user supplied method happens at init time of this handler instead in __call__

    def _create_listener_fn(  # noqa: C901
        self,
        *,
        wants_receive_type: Any,
        can_send_data: bool,
        should_encode_to_json: bool,
        pass_socket: bool,
        callback: AsyncCallable,
    ) -> Callable[..., Coroutine[None, None, None]]:
        json_encoder = JsonEncoder(enc_hook=partial(default_serializer, type_encoders=self.resolve_type_encoders()))

        async def handle_receive(socket: WebSocket) -> Any:
            received_data = await socket.receive_data(mode=self._receive_mode)  # pyright: ignore
            if wants_receive_type is str:
                if isinstance(received_data, bytes):
                    received_data = received_data.decode("utf-8")
            elif wants_receive_type is bytes:
                if isinstance(received_data, str):
                    received_data = received_data.encode("utf-8")
            else:
                received_data = decode_json(received_data)
            return received_data

        async def handle_send(socket: WebSocket, data_to_send: Any) -> None:
            if should_encode_to_json:
                data_to_send = json_encoder.encode(data_to_send)

            await socket.send_data(data_to_send, self._send_mode)  # pyright: ignore

        async def listener_fn(socket: WebSocket, **kwargs: Any) -> None:
            await socket.accept()
            if self._on_accept:
                await self._on_accept(socket)
            if pass_socket:
                kwargs["socket"] = socket
            while True:
                try:
                    received_data = await handle_receive(socket)
                    data_to_send = await callback(data=received_data, **kwargs)
                    if can_send_data:
                        await handle_send(socket, data_to_send)
                except WebSocketDisconnect:
                    if self._on_disconnect:
                        await self._on_disconnect(socket)
                    break

        return listener_fn

    @staticmethod
    def _update_listener_fn_signature(listener_fn: Callable, callback_signature: inspect.Signature) -> None:
        # make our listener_fn look like the callback, so we get a correct signature model

        new_params = [p for p in callback_signature.parameters.values() if p.name not in {"data"}]
        if "socket" not in callback_signature.parameters:
            new_params.append(
                inspect.Parameter(name="socket", kind=inspect.Parameter.KEYWORD_ONLY, annotation="WebSocket")
            )
        new_signature = callback_signature.replace(parameters=new_params)
        listener_fn.__signature__ = new_signature  # type: ignore[attr-defined]
        listener_fn.__annotations__ = {p.name: p.annotation for p in new_signature.parameters.values()}

    def __call__(self, listener_callback: AnyCallable) -> websocket_listener:
        listener_callback_signature = ParsedSignature.from_fn(listener_callback, self.resolve_signature_namespace())

        if "data" not in listener_callback_signature.parameters:
            raise ImproperlyConfiguredException("Websocket listeners must accept a 'data' parameter")
        for param in ("request", "body"):
            if param in listener_callback_signature.parameters:
                raise ImproperlyConfiguredException(f"The {param} kwarg is not supported with websocket listeners")

        listener_callback = AsyncCallable(listener_callback)

        should_encode_to_json = not (
            listener_callback_signature.return_type.is_subclass_of((str, bytes))
            or (
                listener_callback_signature.return_type.is_optional
                and listener_callback_signature.return_type.has_inner_subclass_of((str, bytes))
            )
        )
        can_send_data = not listener_callback_signature.return_type.is_subclass_of(NoneType)
        pass_socket = "socket" in listener_callback_signature.parameters

        listener_fn = self._create_listener_fn(
            callback=listener_callback,
            can_send_data=can_send_data,
            should_encode_to_json=should_encode_to_json,
            wants_receive_type=listener_callback_signature.parameters["data"].annotation,
            pass_socket=pass_socket,
        )
        self._update_listener_fn_signature(listener_fn, listener_callback_signature.original_signature)

        return super().__call__(listener_fn)


class WebsocketListener(ABC):
    path: str | None | list[str] | None = None
    """A path fragment for the route handler function or a sequence of path fragments. If not given defaults to ``/``"""
    dependencies: Dependencies | None = None
    """A string keyed mapping of dependency :class:`Provider <.di.Provide>` instances."""
    dto: type[DTOInterface] | None | EmptyType = Empty
    """:class:`DTOInterface <.dto.interface.DTOInterface>` to use for (de)serializing and validation of request data"""
    exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None
    """A mapping of status codes and/or exception types to handler functions."""
    guards: list[Guard] | None = None
    """A sequence of :class:`Guard <.types.Guard>` callables."""
    middleware: list[Middleware] | None = None
    """A sequence of :class:`Middleware <.types.Middleware>`."""
    receive_mode: WebSocketMode = "text"
    """Websocket mode to receive data in, either `text` or `binary`."""
    send_mode: WebSocketMode = "text"
    """Websocket mode to send data in, either `text` or `binary`."""
    name: str | None = None
    """A string identifying the route handler."""
    opt: dict[str, Any] | None = None
    """
    A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or wherever you
    have access to :class:`Request <.connection.Request>` or :class:`ASGI Scope <.types.Scope>`.
    """
    return_dto: type[DTOInterface] | None | EmptyType = Empty
    """:class:`DTOInterface <.dto.interface.DTOInterface>` to use for serializing outbound response data."""
    signature_namespace: Mapping[str, Any] | None = None
    """
    A mapping of names to types for use in forward reference resolution during signature modelling.
    """
    type_encoders: TypeEncodersMap | None = None
    """
    type_encoders: A mapping of types to callables that transform them into types supported for serialization.
    """

    def __init__(self) -> None:
        self._handler = websocket_listener(
            dependencies=self.dependencies,
            dto=self.dto,
            exception_handlers=self.exception_handlers,
            guards=self.guards,
            middleware=self.middleware,
            send_mode=self.send_mode,
            receive_mode=self.receive_mode,
            name=self.name,
            on_accept=self.on_accept,
            on_disconnect=self.on_disconnect,
            opt=self.opt,
            path=self.path,
            return_dto=self.return_dto,
            signature_namespace=self.signature_namespace,
            type_encoders=self.type_encoders,
        )(self.on_receive)

    def on_accept(self, socket: WebSocket) -> SyncOrAsyncUnion[None]:  # noqa: B027
        """Called after a WebSocket connection has been accepted"""

    @abstractmethod
    def on_receive(self, *args: Any, **kwargs: Any) -> Any:
        """Called after data has been received from the WebSocket.

        This should take a ``data`` argument, receiving the processed WebSocket data,
        and can additionally include handler dependencies such as ``state``, or other
        regular dependencies.

        Data returned from this function will be serialized and sent via the socket
        according to handler configuration.
        """
        raise NotImplementedError

    def on_disconnect(self, socket: WebSocket) -> SyncOrAsyncUnion[None]:  # noqa: B027
        """Called after a WebSocket connection has been disconnected"""
