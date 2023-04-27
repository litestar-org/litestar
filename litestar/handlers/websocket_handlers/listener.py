from __future__ import annotations

from abc import ABC, abstractmethod
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Mapping, cast

from msgspec.json import Encoder as JsonEncoder

from litestar._signature import create_signature_model
from litestar.connection import WebSocket
from litestar.dto.interface import HandlerContext
from litestar.exceptions import ImproperlyConfiguredException
from litestar.serialization import default_serializer
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
from litestar.types.builtin_types import NoneType
from litestar.utils import AsyncCallable
from litestar.utils.signature import ParsedSignature

from . import _utils
from .route_handler import WebsocketRouteHandler

if TYPE_CHECKING:
    from typing import Coroutine

    from litestar import Litestar
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
        "accept_connection_handler",
    )

    def __init__(
        self,
        path: str | None | list[str] | None = None,
        *,
        connection_accept_handler: Callable[[WebSocket], Coroutine[Any, Any, None]] = WebSocket.accept,
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
            connection_accept_handler: A callable that accepts a :class:`WebSocket <.connection.WebSocket>` instance
                and returns a coroutine that when awaited, will accept the connection. Defaults to ``WebSocket.accept``.
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
        self._listener_context = _utils.ListenerContext()
        self._receive_mode: WebSocketMode = receive_mode
        self._send_mode: WebSocketMode = send_mode
        self._on_accept = AsyncCallable(on_accept) if on_accept else None
        self._on_disconnect = AsyncCallable(on_disconnect) if on_disconnect else None
        self.accept_connection_handler = connection_accept_handler
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
        if dto := self.resolve_dto():
            data_parameter = self._listener_context.listener_callback_signature.parameters["data"]
            dto.on_registration(HandlerContext("data", str(self), data_parameter.parsed_type))

        if return_dto := self.resolve_return_dto():
            return_type = self._listener_context.listener_callback_signature.return_type
            return_dto.on_registration(HandlerContext("return", str(self), return_type))

    def __call__(self, listener_callback: AnyCallable) -> websocket_listener:
        self._listener_context.listener_callback = listener_callback
        self._listener_context.handler_function = handler_function = _utils.create_handler_function(
            listener_context=self._listener_context,
            on_accept=self._on_accept,
            on_disconnect=self._on_disconnect,
            accept_connection_handler=self.accept_connection_handler,
        )
        return super().__call__(handler_function)

    def on_registration(self, app: Litestar) -> None:
        self._set_listener_context()
        super().on_registration(app)

    def _create_signature_model(self, app: Litestar) -> None:
        """Create signature model for handler function."""
        if not self.signature_model:
            new_signature = _utils.create_handler_signature(
                self._listener_context.listener_callback_signature.original_signature
            )
            self.signature_model = create_signature_model(
                dependency_name_set=self.dependency_name_set,
                fn=cast("AnyCallable", self.fn.value),
                preferred_validation_backend=app.preferred_validation_backend,
                parsed_signature=ParsedSignature.from_signature(new_signature, self.resolve_signature_namespace()),
            )

    def _set_listener_context(self) -> None:
        listener_context = self._listener_context
        listener_context.listener_callback_signature = listener_callback_signature = ParsedSignature.from_fn(
            listener_context.listener_callback, self.resolve_signature_namespace()
        )

        if "data" not in listener_callback_signature.parameters:
            raise ImproperlyConfiguredException("Websocket listeners must accept a 'data' parameter")

        for param in ("request", "body"):
            if param in listener_callback_signature.parameters:
                raise ImproperlyConfiguredException(f"The {param} kwarg is not supported with websocket listeners")

        listener_context.can_send_data = not listener_callback_signature.return_type.is_subclass_of(NoneType)
        listener_context.pass_socket = "socket" in listener_callback_signature.parameters
        listener_context.resolved_data_dto = resolved_data_dto = self.resolve_dto()
        listener_context.resolved_return_dto = resolved_return_dto = self.resolve_return_dto()
        listener_context.handle_receive = _utils.create_handle_receive(
            resolved_data_dto, self._receive_mode, listener_callback_signature.parameters["data"].annotation
        )
        should_encode_to_json = not (
            listener_callback_signature.return_type.is_subclass_of((str, bytes))
            or (
                listener_callback_signature.return_type.is_optional
                and listener_callback_signature.return_type.has_inner_subclass_of((str, bytes))
            )
        )
        json_encoder = JsonEncoder(enc_hook=partial(default_serializer, type_encoders=self.resolve_type_encoders()))
        listener_context.handle_send = _utils.create_handle_send(
            resolved_return_dto, json_encoder, should_encode_to_json, self._send_mode
        )


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
