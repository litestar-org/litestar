from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any, Callable, Coroutine, cast

from litestar.dto.interface import ConnectionContext
from litestar.serialization import decode_json
from litestar.utils import AsyncCallable

if TYPE_CHECKING:
    from contextlib import AbstractAsyncContextManager

    from msgspec.json import Encoder as JsonEncoder

    from litestar import WebSocket
    from litestar.dto.interface import DTOInterface
    from litestar.types import AnyCallable, TypeEncodersMap
    from litestar.types.asgi_types import WebSocketMode
    from litestar.utils.signature import ParsedSignature


class ListenerContext:
    __slots__ = (
        "can_send_data",
        "handler_function",
        "handle_receive",
        "handle_send",
        "json_encoder",
        "listener_callback",
        "listener_callback_signature",
        "pass_socket",
        "resolved_data_dto",
        "resolved_return_dto",
    )

    can_send_data: bool
    handler_function: AnyCallable
    handle_receive: Callable[[WebSocket, DTOInterface | None], Any]
    handle_send: Callable[[WebSocket, Any, DTOInterface | None], Coroutine[None, None, None]]
    json_encoder: JsonEncoder
    listener_callback: AnyCallable
    listener_callback_signature: ParsedSignature
    pass_socket: bool
    resolved_data_dto: type[DTOInterface] | None
    resolved_return_dto: type[DTOInterface] | None
    resolved_type_encoders: TypeEncodersMap


def create_handle_receive(
    resolved_data_dto: type[DTOInterface] | None,
    receive_mode: WebSocketMode,
    wants_receive_type: type,
) -> Callable[[WebSocket, DTOInterface | None], Coroutine[Any, None, None]]:
    if resolved_data_dto:

        async def handle_receive(socket: WebSocket, dto: DTOInterface | None) -> Any:
            received_data = await socket.receive_data(mode=receive_mode)
            if isinstance(received_data, str):
                received_data = received_data.encode("utf-8")
            return cast("DTOInterface", dto).bytes_to_data_type(received_data)

    elif wants_receive_type is str:

        async def handle_receive(socket: WebSocket, dto: DTOInterface | None) -> Any:
            received_data = await socket.receive_data(mode=receive_mode)
            if isinstance(received_data, bytes):
                return received_data.decode("utf-8")
            return received_data

    elif wants_receive_type is bytes:

        async def handle_receive(socket: WebSocket, dto: DTOInterface | None) -> Any:
            received_data = await socket.receive_data(mode=receive_mode)
            if isinstance(received_data, str):
                return received_data.encode("utf-8")
            return received_data

    else:

        async def handle_receive(socket: WebSocket, dto: DTOInterface | None) -> Any:
            received_data = await socket.receive_data(mode=receive_mode)
            return decode_json(received_data)

    return handle_receive


def create_handle_send(
    resolved_return_dto: type[DTOInterface] | None,
    json_encoder: JsonEncoder,
    should_encode_to_json: bool,
    send_mode: WebSocketMode,
) -> Callable[[WebSocket, Any, DTOInterface | None], Coroutine[None, None, None]]:
    if resolved_return_dto:

        async def handle_send(socket: WebSocket, data_to_send: Any, dto: DTOInterface | None) -> None:
            data_to_send = json_encoder.encode(cast("DTOInterface", dto).data_to_encodable_type(data_to_send))
            await socket.send_data(data_to_send, send_mode)  # pyright: ignore

    elif should_encode_to_json:

        async def handle_send(socket: WebSocket, data_to_send: Any, dto: DTOInterface | None) -> None:
            data_to_send = json_encoder.encode(data_to_send)
            await socket.send_data(data_to_send, send_mode)  # pyright: ignore

    else:

        async def handle_send(socket: WebSocket, data_to_send: Any, dto: DTOInterface | None) -> None:
            await socket.send_data(data_to_send, send_mode)  # pyright: ignore

    return handle_send


def create_handler_function(
    listener_context: ListenerContext,
    lifespan_manager: Callable[[WebSocket], AbstractAsyncContextManager],
) -> Callable[..., Coroutine[None, None, None]]:
    listener_callback = AsyncCallable(listener_context.listener_callback)

    async def handler_fn(*args: Any, socket: WebSocket, **kwargs: Any) -> None:
        ctx = ConnectionContext.from_connection(socket)
        data_dto = listener_context.resolved_data_dto(ctx) if listener_context.resolved_data_dto else None
        return_dto = listener_context.resolved_return_dto(ctx) if listener_context.resolved_return_dto else None
        handle_receive = listener_context.handle_receive
        handle_send = listener_context.handle_send if listener_context.can_send_data else None

        if listener_context.pass_socket:
            kwargs["socket"] = socket

        async with lifespan_manager(socket):
            while True:
                received_data = await handle_receive(socket, data_dto)
                data_to_send = await listener_callback(*args, data=received_data, **kwargs)
                if handle_send:
                    await handle_send(socket, data_to_send, return_dto)

    return handler_fn


def create_handler_signature(callback_signature: inspect.Signature) -> inspect.Signature:
    """Creates a :class:`inspect.Signature` for the handler function for signature modelling.

    This is required for two reasons:

        1. the :class:`.handlers.WebsocketHandler` signature model cannot contain the ``data`` parameter, which is
            required for :class:`.handlers.websocket_listener` handlers.
        2. the :class;`.handlers.WebsocketHandler` signature model must include the ``socket`` parameter, which is
            optional for :class:`.handlers.websocket_listener` handlers.

    Args:
        callback_signature: The :class:`inspect.Signature` of the listener callback.

    Returns:
        The :class:`inspect.Signature` for the listener callback as required for signature modelling.
    """
    new_params = [p for p in callback_signature.parameters.values() if p.name not in {"data"}]
    if "socket" not in callback_signature.parameters:
        new_params.append(inspect.Parameter(name="socket", kind=inspect.Parameter.KEYWORD_ONLY, annotation="WebSocket"))
    return callback_signature.replace(parameters=new_params)
