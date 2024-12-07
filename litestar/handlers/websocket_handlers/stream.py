from __future__ import annotations

import functools
import inspect
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Mapping

import anyio

from litestar.handlers.websocket_handlers.route_handler import WebsocketRouteHandler

if TYPE_CHECKING:
    from litestar import WebSocket
    from litestar.types import Dependencies, ExceptionHandler, Guard, Middleware
    from litestar.types.asgi_types import WebSocketMode


async def send_websocket_stream(
    socket: WebSocket,
    stream: AsyncGenerator[str | bytes, Any],
    close: bool = True,
    mode: WebSocketMode = "text",
    listen_for_disconnect: bool = False,
) -> None:
    if listen_for_disconnect:
        async with anyio.create_task_group() as tg:
            tg.start_soon(socket.receive_data, "text")
            tg.start_soon(socket.send_stream, stream, mode)
    else:
        await socket.send_stream(stream=stream, mode=mode)

    if close:
        await socket.close()


def websocket_stream(
    path: str | list[str] | None = None,
    *,
    dependencies: Dependencies | None = None,
    exception_handlers: dict[int | type[Exception], ExceptionHandler] | None = None,
    guards: list[Guard] | None = None,
    middleware: list[Middleware] | None = None,
    name: str | None = None,
    opt: dict[str, Any] | None = None,
    signature_namespace: Mapping[str, Any] | None = None,
    websocket_class: type[WebSocket] | None = None,
    mode: WebSocketMode = "text",
    listen_for_disconnect: bool = True,
    **kwargs: Any,
) -> Callable[[Callable[..., AsyncGenerator[str | bytes, Any]]], WebsocketRouteHandler]:
    def decorator(fn: Callable[..., AsyncGenerator[str | bytes, Any]]) -> WebsocketRouteHandler:
        signature = inspect.signature(fn)
        generator_receives_socket = "socket" in signature.parameters

        @functools.wraps(fn)
        async def handler(socket: WebSocket, **kw: Any) -> None:
            if generator_receives_socket:
                kw["socket"] = socket

            await send_websocket_stream(
                socket=socket,
                stream=fn(**kw),
                mode=mode,
                close=True,
                listen_for_disconnect=listen_for_disconnect,
            )

        handler.__annotations__ = fn.__annotations__
        handler.__annotations__["return"] = None

        if not generator_receives_socket:
            handler.__annotations__["socket"] = "WebSocket"

        new_params = dict(signature.parameters)
        new_signature = signature
        if not generator_receives_socket:
            new_signature = new_signature.replace(
                parameters=[
                    *new_params.values(),
                    inspect.Parameter(name="socket", annotation="WebSocket", kind=inspect.Parameter.KEYWORD_ONLY),
                ]
            )

        handler.__signature__ = new_signature  # type: ignore[attr-defined]

        return WebsocketRouteHandler(
            path=path,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guard=guards,
            middleware=middleware,
            name=name,
            oprt=opt,
            signature_namespace=signature_namespace,
            websocket_class=websocket_class,
            **kwargs,
        )(handler)

    return decorator
