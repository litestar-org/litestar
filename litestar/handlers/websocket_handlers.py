from __future__ import annotations

import inspect
from inspect import Signature
from typing import TYPE_CHECKING, Literal

from litestar.exceptions import ImproperlyConfiguredException, WebSocketDisconnect
from litestar.handlers.base import BaseRouteHandler
from litestar.types.builtin_types import NoneType
from litestar.types.empty import Empty
from litestar.utils import AsyncCallable, Ref, is_async_callable

__all__ = ("WebsocketRouteHandler", "websocket", "websocket_listener")

if TYPE_CHECKING:
    from typing import Any, Mapping

    from litestar.dto.interface import DTOInterface
    from litestar.connection import WebSocket
    from litestar.types import (
        AnyCallable,
        AsyncAnyCallable,
        Dependencies,
        EmptyType,
        ExceptionHandler,
        Guard,
        MaybePartial,  # noqa: F401
        Middleware,
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
    and invokes a callback function every time new data is received.
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
        **kwargs: Any,
    ) -> None:
        self.mode = mode
        self._pass_socket = False
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
        self._validate_listener_callback(listener_callback)

        listener_callback_signature = inspect.signature(listener_callback)

        if not is_async_callable(listener_callback):
            listener_callback = AsyncCallable(listener_callback)

        async def listener_fn(socket: WebSocket, **kwargs: Any) -> None:
            await socket.accept()
            if self._pass_socket:
                kwargs["socket"] = socket
            while True:
                try:
                    data = await socket.receive_data(mode=self.mode)  # pyright: ignore
                    await listener_callback(data=data, **kwargs)
                except WebSocketDisconnect:
                    break

        # make our listener_fn look like the callback, so we get a correct signature model
        new_params = [p for p in listener_callback_signature.parameters.values() if p.name not in {"data"}]
        if "socket" not in listener_callback_signature.parameters:
            new_params.append(
                inspect.Parameter(name="socket", kind=inspect.Parameter.KEYWORD_ONLY, annotation="WebSocket")
            )
        else:
            self._pass_socket = True

        listener_fn.__signature__ = listener_callback_signature.replace(parameters=new_params)  # type: ignore[attr-defined]

        self.fn = Ref(listener_fn)
        self.signature = Signature.from_callable(listener_fn)
        return self

    @staticmethod
    def _validate_listener_callback(fn: AnyCallable) -> None:
        """Validate the route handler function once it's set by inspecting its return annotations."""
        signature = inspect.signature(fn)

        if signature.return_annotation not in {None, "None"}:
            raise ImproperlyConfiguredException("Websocket listeners should return 'None'")
        if "data" not in signature.parameters:
            raise ImproperlyConfiguredException("Websocket listeners must accept a 'data' parameter")
        for param in ("request", "body"):
            if param in signature.parameters:
                raise ImproperlyConfiguredException(f"The {param} kwarg is not supported with websocket listeners")
