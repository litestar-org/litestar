from __future__ import annotations

import inspect
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Callable, Literal

from litestar.exceptions import ImproperlyConfiguredException, WebSocketDisconnect
from litestar.handlers.base import BaseRouteHandler
from litestar.serialization import decode_json
from litestar.types.parsed_signature import ParsedSignature
from litestar.types.builtin_types import NoneType
from litestar.types.empty import Empty
from litestar.utils import AsyncCallable, is_async_callable

__all__ = ("WebsocketRouteHandler", "websocket", "websocket_listener", "WebsocketListener")

if TYPE_CHECKING:
    from typing import Any, Mapping

    from litestar.dto.interface import DTOInterface
    from litestar.connection import WebSocket
    from litestar.types import (
        AnyCallable,
        Dependencies,
        EmptyType,
        ExceptionHandler,
        Guard,
        MaybePartial,  # noqa: F401
        Middleware,
        SyncOrAsyncUnion,
    )

__all__ = ("WebsocketRouteHandler", "websocket")


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
        name: str | None = None,
        opt: dict[str, Any] | None = None,
        signature_namespace: Mapping[str, Any] | None = None,
        mode: Literal["text", "binary"] = "text",
        on_accept: Callable[[WebSocket], SyncOrAsyncUnion[None]] | None = None,
        on_disconnect: Callable[[WebSocket], SyncOrAsyncUnion[None]] | None = None,
        **kwargs: Any,
    ) -> None:
        self._mode = mode
        self._pass_socket = False
        self._on_accept = AsyncCallable(on_accept) if on_accept else None
        self._on_disconnect = AsyncCallable(on_disconnect) if on_disconnect else None

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

    def __call__(self, listener_callback: AnyCallable) -> websocket_listener:
        listener_callback_signature = ParsedSignature.from_fn(listener_callback, self.resolve_signature_namespace())
        raw_listener_callback_signature = listener_callback_signature.original_signature

        if "data" not in listener_callback_signature.parameters:
            raise ImproperlyConfiguredException("Websocket listeners must accept a 'data' parameter")
        for param in ("request", "body"):
            if param in listener_callback_signature.parameters:
                raise ImproperlyConfiguredException(f"The {param} kwarg is not supported with websocket listeners")

        if not is_async_callable(listener_callback):
            listener_callback = AsyncCallable(listener_callback)

        should_receive_json = not listener_callback_signature.parameters["data"].parsed_type.is_subclass_of(
            (str, bytes)
        )

        async def listener_fn(socket: WebSocket, **kwargs: Any) -> None:
            await socket.accept()
            if self._on_accept:
                await self._on_accept(socket)
            if self._pass_socket:
                kwargs["socket"] = socket
            while True:
                try:
                    received_data = await socket.receive_data(mode=self._mode)  # pyright: ignore
                    if should_receive_json:
                        received_data = decode_json(received_data)
                    data_to_send = await listener_callback(data=received_data, **kwargs)
                    if isinstance(data_to_send, str):
                        await socket.send_text(data_to_send)
                    elif isinstance(data_to_send, bytes):
                        await socket.send_bytes(data_to_send)
                    else:
                        await socket.send_json(data_to_send)
                except WebSocketDisconnect:
                    if self._on_disconnect:
                        await self._on_disconnect(socket)
                    break

        # make our listener_fn look like the callback, so we get a correct signature model
        new_params = [p for p in raw_listener_callback_signature.parameters.values() if p.name not in {"data"}]
        if "socket" not in raw_listener_callback_signature.parameters:
            new_params.append(
                inspect.Parameter(name="socket", kind=inspect.Parameter.KEYWORD_ONLY, annotation="WebSocket")
            )
        else:
            self._pass_socket = True

        new_signature = raw_listener_callback_signature.replace(parameters=new_params)
        listener_fn.__signature__ = new_signature  # type: ignore[attr-defined]
        for param in new_signature.parameters.values():
            listener_fn.__annotations__[param.name] = param.annotation

        return super().__call__(listener_fn)


class WebsocketListener(ABC):
    path: str | None | list[str] | None = None
    dependencies: Dependencies | None = None
    exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None
    guards: list[Guard] | None = None
    middleware: list[Middleware] | None = None
    name: str | None = None
    opt: dict[str, Any] | None = None
    signature_namespace: Mapping[str, Any] | None = None
    mode: Literal["text", "binary"] = "text"

    def __init__(self) -> None:
        self._handler = websocket_listener(
            path=self.path,
            dependencies=self.dependencies,
            exception_handlers=self.exception_handlers,
            guards=self.guards,
            middleware=self.middleware,
            name=self.name,
            opt=self.opt,
            signature_namespace=self.signature_namespace,
            mode=self.mode,
            on_accept=self.on_accept,
            on_disconnect=self.on_disconnect,
        )(self.on_receive)

    def on_accept(self, socket: WebSocket) -> SyncOrAsyncUnion[None]:  # noqa: B027
        pass

    @abstractmethod
    def on_receive(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def on_disconnect(self, socket: WebSocket) -> SyncOrAsyncUnion[None]:  # noqa: B027
        pass
