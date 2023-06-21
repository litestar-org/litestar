from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    Mapping,
    Optional,
    cast,
    overload,
)

from msgspec.json import Encoder as JsonEncoder

from litestar._signature import SignatureModel
from litestar.connection import WebSocket
from litestar.dto.interface import HandlerContext
from litestar.exceptions import ImproperlyConfiguredException, WebSocketDisconnect
from litestar.serialization import default_serializer
from litestar.types import (
    AnyCallable,
    Dependencies,
    Empty,
    EmptyType,
    ExceptionHandler,
    Guard,
    Middleware,
    TypeEncodersMap,
)
from litestar.types.builtin_types import NoneType
from litestar.utils import AsyncCallable
from litestar.utils.signature import ParsedSignature

from ._utils import (
    ListenerContext,
    create_handle_receive,
    create_handle_send,
    create_handler_function,
    create_handler_signature,
    create_stub_dependency,
)
from .route_handler import WebsocketRouteHandler

if TYPE_CHECKING:
    from typing import Coroutine

    from litestar import Litestar, Router
    from litestar.dto.interface import DTOInterface
    from litestar.types.asgi_types import WebSocketMode


__all__ = ("WebsocketListener", "websocket_listener")


class websocket_listener(WebsocketRouteHandler):
    """A websocket listener that automatically accepts a connection, handles disconnects,
    invokes a callback function every time new data is received and sends any data
    returned
    """

    __slots__ = {
        "connection_accept_handler": "Callback to accept a WebSocket connection. By default, calls WebSocket.accept",
        "on_accept": "Callback invoked after a WebSocket connection has been accepted",
        "on_disconnect": "Callback invoked after a WebSocket connection has been closed",
        "_initialized": None,
        "_pass_socket": None,
        "_receive_mode": None,
        "_send_mode": None,
        "_listener_context": None,
        "_connection_lifespan": None,
        "_dependency_stubs": None,
    }

    @overload
    def __init__(
        self,
        path: str | None | list[str] | None = None,
        *,
        connection_lifespan: Callable[..., AbstractAsyncContextManager[Any]] | None = None,
        dependencies: Dependencies | None = None,
        dto: type[DTOInterface] | None | EmptyType = Empty,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        guards: list[Guard] | None = None,
        middleware: list[Middleware] | None = None,
        receive_mode: WebSocketMode = "text",
        send_mode: WebSocketMode = "text",
        name: str | None = None,
        opt: dict[str, Any] | None = None,
        return_dto: type[DTOInterface] | None | EmptyType = Empty,
        signature_namespace: Mapping[str, Any] | None = None,
        type_encoders: TypeEncodersMap | None = None,
        **kwargs: Any,
    ) -> None:
        ...

    @overload
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
        on_accept: AnyCallable | None = None,
        on_disconnect: AnyCallable | None = None,
        opt: dict[str, Any] | None = None,
        return_dto: type[DTOInterface] | None | EmptyType = Empty,
        signature_namespace: Mapping[str, Any] | None = None,
        type_encoders: TypeEncodersMap | None = None,
        **kwargs: Any,
    ) -> None:
        ...

    def __init__(
        self,
        path: str | None | list[str] | None = None,
        *,
        connection_accept_handler: Callable[[WebSocket], Coroutine[Any, Any, None]] = WebSocket.accept,
        connection_lifespan: Callable[..., AbstractAsyncContextManager[Any]] | None = None,
        dependencies: Dependencies | None = None,
        dto: type[DTOInterface] | None | EmptyType = Empty,
        exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
        guards: list[Guard] | None = None,
        middleware: list[Middleware] | None = None,
        receive_mode: WebSocketMode = "text",
        send_mode: WebSocketMode = "text",
        name: str | None = None,
        on_accept: AnyCallable | None = None,
        on_disconnect: AnyCallable | None = None,
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
            connection_lifespan: An asynchronous context manager, handling the lifespan of the connection. By default,
                it calls the ``connection_accept_handler``, ``on_connect`` and ``on_disconnect``. Can request any
                dependencies, for example the :class:`WebSocket <.connection.WebSocket>` connection
            dependencies: A string keyed mapping of dependency :class:`Provider <.di.Provide>` instances.
            dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for (de)serializing and
                validation of request data.
            exception_handlers: A mapping of status codes and/or exception types to handler functions.
            guards: A sequence of :class:`Guard <.types.Guard>` callables.
            middleware: A sequence of :class:`Middleware <.types.Middleware>`.
            receive_mode: Websocket mode to receive data in, either `text` or `binary`.
            send_mode: Websocket mode to receive data in, either `text` or `binary`.
            name: A string identifying the route handler.
            on_accept: Callback invoked after a connection has been accepted. Can request any dependencies, for example
                the :class:`WebSocket <.connection.WebSocket>` connection
            on_disconnect: Callback invoked after a connection has been closed. Can request any dependencies, for
                example the :class:`WebSocket <.connection.WebSocket>` connection
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
        if connection_lifespan and any([on_accept, on_disconnect, connection_accept_handler is not WebSocket.accept]):
            raise ImproperlyConfiguredException(
                "connection_lifespan can not be used with connection hooks "
                "(on_accept, on_disconnect, connection_accept_handler)",
            )
        self._listener_context = ListenerContext()
        self._receive_mode: WebSocketMode = receive_mode
        self._send_mode: WebSocketMode = send_mode
        self._connection_lifespan = connection_lifespan

        self.connection_accept_handler = connection_accept_handler
        self.on_accept = AsyncCallable(on_accept) if on_accept else None
        self.on_disconnect = AsyncCallable(on_disconnect) if on_disconnect else None
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

        # its important that this is assigned after the super() call
        self.dto = dto
        self.return_dto = return_dto

        if not self.dependencies:
            self.dependencies = {}

        self.dependencies = dict(self.dependencies)
        self.dependencies["connection_lifespan_dependencies"] = create_stub_dependency(
            self._connection_lifespan or self.default_connection_lifespan
        )

        if self.on_accept:
            self.dependencies["on_accept_dependencies"] = create_stub_dependency(self.on_accept.ref.value)

        if self.on_disconnect:
            self.dependencies["on_disconnect_dependencies"] = create_stub_dependency(self.on_disconnect.ref.value)

    @asynccontextmanager
    async def default_connection_lifespan(
        self,
        socket: WebSocket,
        on_accept_dependencies: Optional[Dict[str, Any]] = None,  # noqa: UP007, UP006
        on_disconnect_dependencies: Optional[Dict[str, Any]] = None,  # noqa: UP007, UP006
    ) -> AsyncGenerator[None, None]:
        """Handle the connection lifespan of a :class:`WebSocket <.connection.WebSocket>`.

        Args:
            socket: The :class:`WebSocket <.connection.WebSocket>` connection
            on_accept_dependencies: Dependencies requested by the :attr:`on_accept` hook
            on_disconnect_dependencies: Dependencies requested by the :attr:`on_disconnect` hook

        By, default this will

            - Call :attr:`connection_accept_handler` to accept a connection
            - Call :attr:`on_accept` if defined after a connection has been accepted
            - Call :attr:`on_disconnect` upon leaving the context
        """
        await self.connection_accept_handler(socket)

        if self.on_accept:
            await self.on_accept(**(on_accept_dependencies or {}))

        try:
            yield
        except WebSocketDisconnect:
            pass
        finally:
            if self.on_disconnect:
                await self.on_disconnect(**(on_disconnect_dependencies or {}))

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once it's set by inspecting its return annotations."""
        # since none of the validation rules of WebsocketRouteHandler apply here, this is let empty. Validation of the
        # user supplied method happens at init time of this handler instead in __call__

    def _init_handler_dtos(self) -> None:
        """Initialize the data and return DTOs for the handler."""
        if dto := self.resolve_dto():
            data_parameter = self._listener_context.listener_callback_signature.parameters["data"]
            dto.on_registration(HandlerContext(dto_for="data", handler_id=str(self), field_definition=data_parameter))

        if return_dto := self.resolve_return_dto():
            return_type = self._listener_context.listener_callback_signature.return_type
            return_dto.on_registration(
                HandlerContext(dto_for="return", handler_id=str(self), field_definition=return_type)
            )

    def __call__(self, listener_callback: AnyCallable) -> websocket_listener:
        self._listener_context.listener_callback = listener_callback
        self._listener_context.handler_function = handler_function = create_handler_function(
            listener_context=self._listener_context,
            lifespan_manager=self._connection_lifespan or self.default_connection_lifespan,
        )
        return super().__call__(handler_function)

    def on_registration(self, app: Litestar) -> None:
        self._set_listener_context()
        super().on_registration(app)

    def _create_signature_model(self, app: Litestar) -> None:
        """Create signature model for handler function."""
        if not self.signature_model:
            new_signature = create_handler_signature(
                self._listener_context.listener_callback_signature.original_signature
            )
            self.signature_model = SignatureModel.create(
                dependency_name_set=self.dependency_name_set,
                fn=cast("AnyCallable", self.fn.value),
                parsed_signature=ParsedSignature.from_signature(new_signature, self.resolve_signature_namespace()),
            )

    def _set_listener_context(self) -> None:
        listener_callback_signature = ParsedSignature.from_fn(
            self._listener_context.listener_callback, self.resolve_signature_namespace()
        )

        if "data" not in listener_callback_signature.parameters:
            raise ImproperlyConfiguredException("Websocket listeners must accept a 'data' parameter")

        for param in ("request", "body"):
            if param in listener_callback_signature.parameters:
                raise ImproperlyConfiguredException(f"The {param} kwarg is not supported with websocket listeners")

        resolved_data_dto = self.resolve_dto()
        resolved_return_dto = self.resolve_return_dto()

        self._listener_context.listener_callback_signature = listener_callback_signature
        self._listener_context.can_send_data = not listener_callback_signature.return_type.is_subclass_of(NoneType)
        self._listener_context.pass_socket = "socket" in listener_callback_signature.parameters
        self._listener_context.resolved_data_dto = resolved_data_dto
        self._listener_context.resolved_return_dto = resolved_return_dto
        self._listener_context.handle_receive = create_handle_receive(
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

        self._listener_context.handle_send = create_handle_send(
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
    on_accept: AnyCallable | None = None
    """Called after a :class:`WebSocket <.connection.WebSocket>` connection has been accepted. Can receive any dependencies"""
    on_disconnect: AnyCallable | None = None
    """Called after a :class:`WebSocket <.connection.WebSocket>` connection has been disconnected. Can receive any dependencies"""
    receive_mode: WebSocketMode = "text"
    """:class:`WebSocket <.connection.WebSocket>` mode to receive data in, either ``text`` or ``binary``."""
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

    def __init__(self, owner: Router) -> None:
        """Initialize a WebsocketListener instance.

        Args:
            owner: The :class:`Router <.router.Router>` instance that owns this listener.
        """
        self._owner = owner

    def to_handler(self) -> websocket_listener:
        handler = websocket_listener(
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
        handler.owner = self._owner
        return handler

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
