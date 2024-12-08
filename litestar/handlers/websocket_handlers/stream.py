from __future__ import annotations

import functools
import inspect
import warnings
from typing import TYPE_CHECKING, Any, AsyncGenerator, Callable, Mapping

import anyio

from litestar.exceptions import LitestarWarning, WebSocketDisconnect
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
    warn_on_data_discard: bool = True,
) -> None:
    """
    Stream data to the ``socket`` from an asynchronous generator.

    Example:
        Sending the current time to the connected client every 0.5 seconds:

        .. code-block:: python

            async def stream_current_time() -> AsyncGenerator[str, None]:
                while True:
                    yield str(time.time())
                    await asyncio.sleep(0.5)


            @websocket("/time")
            async def time_handler(socket: WebSocket) -> None:
                await socket.accept()
                await send_websocket_stream(
                    socket,
                    stream_current_time(),
                    listen_for_disconnect=True,
                )


    Args:
        socket: The :class:`~litestar.connection.WebSocket` to send to
        stream: An asynchronous generator yielding data to send
        close: If ``True``, close the socket after the generator is exhausted
        mode: WebSocket mode to use for sending
        listen_for_disconnect: If ``True``, listen for client disconnects in the background. If a client disconnects,
            stop the generator and cancel sending data. Should always be ``True`` unless disconnects are handled
            elsewhere, for example by reading data from the socket concurrently. Should never be set to ``True`` when
            reading data from socket concurrently, as it can lead to data loss
        warn_on_data_discard: If ``True`` and ``listen_for_disconnect=True``, warn if during listening for client
            disconnects, data is received from the socket
    """
    if listen_for_disconnect:
        # wrap 'send_stream' and disconnect listener, so they'll cancel the other once
        # one of the finishes
        async def wrapped_stream() -> None:
            await socket.send_stream(stream, mode=mode)
            # stream exhausted, we can stop listening for a disconnect
            tg.cancel_scope.cancel()

        async def disconnect_listener() -> None:
            try:
                # run this in a loop - we might receive other data than disconnects.
                # listen_for_disconnect is explicitly not safe when consuming WS data
                # in other places, so discarding that data here is fine
                while True:
                    await socket.receive_data("text")
                    if warn_on_data_discard:
                        warnings.warn(
                            "received data from websocket while listening for client"
                            "disconnect in a websocket_stream. listen_for_disconnect is"
                            "not safe to use when attempting to receive data from the "
                            "same socket concurrently with a websocket_stream. set "
                            "listen_for_disconnect=False if you're attempting to "
                            "receive data from this socket or set "
                            "warn_on_data_discard=False to disable this warning",
                            stacklevel=2,
                            category=LitestarWarning,
                        )
            except WebSocketDisconnect:
                # client disconnected, we can stop streaming
                tg.cancel_scope.cancel()

        async with anyio.create_task_group() as tg:
            tg.start_soon(wrapped_stream)
            tg.start_soon(disconnect_listener)

    else:
        await socket.send_stream(stream=stream, mode=mode)

    if close and socket.connection_state != "disconnect":
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
    warn_on_data_discard: bool = True,
    **kwargs: Any,
) -> Callable[[Callable[..., AsyncGenerator[str | bytes, Any]]], WebsocketRouteHandler]:
    """
    Create a WebSocket handler that accepts a connection and sends data to it from an
    async generator.

    Example:
        Sending the current time to the connected client every 0.5 seconds:

        .. code-block:: python
            @websocket_stream("/time")
            async def send_time() -> AsyncGenerator[str, None]:
                while True:
                    yield str(time.time())
                    await asyncio.sleep(0.5)

    Args:
        path: A path fragment for the route handler function or a sequence of path fragments. If not given defaults
            to ``/``
        dependencies: A string keyed mapping of dependency :class:`Provider <.di.Provide>` instances.
        exception_handlers: A mapping of status codes and/or exception types to handler functions.
        guards: A sequence of :class:`Guard <.types.Guard>` callables.
        middleware: A sequence of :class:`Middleware <.types.Middleware>`.
        name: A string identifying the route handler.
        opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
            wherever you have access to :class:`Request <.connection.Request>` or
            :class:`ASGI Scope <.types.Scope>`.
        signature_namespace: A mapping of names to types for use in forward reference resolution during signature modelling.
        websocket_class: A custom subclass of :class:`WebSocket <.connection.WebSocket>` to be used as route handler's
            default websocket class.
        mode: WebSocket mode used for sending
        listen_for_disconnect: If ``True``, listen for client disconnects in the background. If a client disconnects,
            stop the generator and cancel sending data. Should always be ``True`` unless disconnects are handled
            elsewhere, for example by reading data from the socket concurrently. Should never be set to ``True`` when
            reading data from socket concurrently, as it can lead to data loss
        warn_on_data_discard: If ``True`` and ``listen_for_disconnect=True``, warn if during listening for client
            disconnects, data is received from the socket
        **kwargs: Any additional kwarg - will be set in the opt dictionary.
    """

    def decorator(fn: Callable[..., AsyncGenerator[str | bytes, Any]]) -> WebsocketRouteHandler:
        signature = inspect.signature(fn)
        generator_receives_socket = "socket" in signature.parameters

        @functools.wraps(fn)
        async def handler(*args: Any, socket: WebSocket, **kw: Any) -> None:
            if generator_receives_socket:
                kw["socket"] = socket

            await send_websocket_stream(
                socket=socket,
                stream=fn(*args, **kw),
                mode=mode,
                close=True,
                listen_for_disconnect=listen_for_disconnect,
                warn_on_data_discard=warn_on_data_discard,
            )

        handler.__annotations__ = fn.__annotations__
        handler.__annotations__["return"] = None

        if not generator_receives_socket:
            handler.__annotations__["socket"] = "WebSocket"

        new_signature = signature
        if not generator_receives_socket:
            new_signature = new_signature.replace(
                parameters=[
                    *signature.parameters.values(),
                    inspect.Parameter(name="socket", annotation="WebSocket", kind=inspect.Parameter.KEYWORD_ONLY),
                ],
                return_annotation=None,
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
