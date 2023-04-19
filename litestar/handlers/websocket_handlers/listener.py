from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, Callable, Mapping

from litestar.types import (
    AnyCallable,
    Dependencies,
    Empty,
    EmptyType,
    ExceptionHandler,
    Guard,
    Middleware,
    SyncOrAsyncUnion,
    TypeEncodersMap,
)
from litestar.utils import AsyncCallable

from ._utils import (
    _create_handler_function,
    _ListenerContext,
    _set_listener_context,
    _update_listener_fn_signature,
)
from .route_handler import WebsocketRouteHandler

if TYPE_CHECKING:
    from litestar import Litestar, WebSocket
    from litestar.dto.interface import DTOInterface
    from litestar.types.asgi_types import WebSocketMode

__all__ = (
    "WebsocketListener",
    "websocket_listener",
)


class websocket_listener(WebsocketRouteHandler):
    """A websocket listener that automatically accepts a connection, handles disconnects,
    invokes a callback function every time new data is received and sends any data
    returned
    """

    __slots__ = (
        "_on_accept",
        "_on_disconnect",
        "_pass_socket",
        "_receive_mode",
        "_send_mode",
        "_listener_context",
    )

    def __init__(
        self,
        path: str | None | list[str] | None = None,
        *,
        dependencies: Dependencies | None = None,
        dto: type[DTOInterface] | None | EmptyType = Empty,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        guards: list[Guard] | None = None,
        middleware: list[Middleware] | None = None,
        receive_mode: WebSocketMode = "text",
        send_mode: WebSocketMode = "text",
        name: str | None = None,
        on_accept: Callable[[WebSocket], SyncOrAsyncUnion[None]] | None = None,
        on_disconnect: Callable[[WebSocket], SyncOrAsyncUnion[None]] | None = None,
        opt: dict[str, Any] | None = None,
        return_dto: type[DTOInterface] | None | EmptyType = Empty,
        signature_namespace: Mapping[str, Any] | None = None,
        type_encoders: TypeEncodersMap | None = None,
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
            return_dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for serializing
                outbound response data.
            signature_namespace: A mapping of names to types for use in forward reference resolution during signature
                modelling.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        self._listener_context = _ListenerContext()
        self._receive_mode: WebSocketMode = receive_mode
        self._send_mode: WebSocketMode = send_mode
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

        # need to be assigned after the super() call
        self.dto = dto
        self.return_dto = return_dto

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it's set by inspecting its return annotations."""
        # since none of the validation rules of WebsocketRouteHandler apply here, this is let empty. Validation of the
        # user supplied method happens at init time of this handler instead in __call__

    def _init_handler_dtos(self) -> None:
        """Initialize the data and return DTOs for the handler."""
        data_parameter = self._listener_context.listener_callback_signature.parameters["data"]
        if dto := self.resolve_dto():
            dto.on_registration(self, "data", data_parameter.parsed_type)

        return_type = self._listener_context.listener_callback_signature.return_type
        if return_dto := self.resolve_return_dto():
            return_dto.on_registration(self, "return", return_type)

    def __call__(self, listener_callback: AnyCallable) -> websocket_listener:
        self._listener_context.listener_callback = listener_callback
        self._listener_context.handler_function = handler_function = _create_handler_function(
            listener_context=self._listener_context,
            on_accept=self._on_accept,
            on_disconnect=self._on_disconnect,
        )
        return super().__call__(handler_function)

    def on_registration(self, app: Litestar) -> None:
        _set_listener_context(
            listener_context=self._listener_context,
            receive_mode=self._receive_mode,
            send_mode=self._send_mode,
            resolved_data_dto=self.resolve_dto(),
            resolved_return_dto=self.resolve_return_dto(),
            resolved_signature_namespace=self.resolve_signature_namespace(),
            resolved_type_encoders=self.resolve_type_encoders(),
        )
        _update_listener_fn_signature(self._listener_context)

        # must call this after listener fn signature has been updated, as we assume that
        # the `parsed_fn_signature` property will be accessed somewhere in the MRO above us.
        super().on_registration(app)


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
