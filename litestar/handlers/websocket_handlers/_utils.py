from __future__ import annotations

import inspect
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Coroutine, cast

from msgspec.json import Encoder as JsonEncoder

from litestar.exceptions import ImproperlyConfiguredException, WebSocketDisconnect
from litestar.serialization import decode_json, default_serializer
from litestar.types.builtin_types import NoneType
from litestar.utils import AsyncCallable
from litestar.utils.signature import ParsedSignature

if TYPE_CHECKING:
    from litestar import WebSocket
    from litestar.dto.interface import DTOInterface
    from litestar.types import AnyCallable, TypeEncodersMap
    from litestar.types.asgi_types import WebSocketMode


class _ListenerContext:
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


def _update_listener_fn_signature(listener_context: _ListenerContext) -> None:
    # make our listener_fn look like the callback, so we get a correct signature model

    callback_signature = listener_context.listener_callback_signature.original_signature
    new_params = [p for p in callback_signature.parameters.values() if p.name not in {"data"}]
    if "socket" not in callback_signature.parameters:
        new_params.append(inspect.Parameter(name="socket", kind=inspect.Parameter.KEYWORD_ONLY, annotation="WebSocket"))
    # TODO: could this be avoided if logic for construction of a signature model were moved on to the route handler?
    new_signature = callback_signature.replace(parameters=new_params)
    listener_context.handler_function.__signature__ = new_signature  # type: ignore[attr-defined]
    listener_context.handler_function.__annotations__ = {
        p.name: p.annotation for p in new_signature.parameters.values()
    }


def _create_handle_receive(
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


def _create_handle_send(
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


def _create_handler_function(
    listener_context: _ListenerContext,
    on_accept: AsyncCallable | None,
    on_disconnect: AsyncCallable | None,
) -> Callable[..., Coroutine[None, None, None]]:
    async def listener_fn(socket: WebSocket, **kwargs: Any) -> None:
        await socket.accept()

        listener_callback = AsyncCallable(listener_context.listener_callback)
        data_dto = listener_context.resolved_data_dto(socket) if listener_context.resolved_data_dto else None
        return_dto = listener_context.resolved_return_dto(socket) if listener_context.resolved_return_dto else None

        if on_accept:
            await on_accept(socket)

        if listener_context.pass_socket:
            kwargs["socket"] = socket

        while True:
            try:
                received_data = await listener_context.handle_receive(socket, data_dto)
                data_to_send = await listener_callback(data=received_data, **kwargs)
                if listener_context.can_send_data:
                    await listener_context.handle_send(socket, data_to_send, return_dto)
            except WebSocketDisconnect:
                if on_disconnect:
                    await on_disconnect(socket)
                break

    return listener_fn


def _set_listener_context(
    listener_context: _ListenerContext,
    receive_mode: WebSocketMode,
    send_mode: WebSocketMode,
    resolved_data_dto: type[DTOInterface] | None,
    resolved_return_dto: type[DTOInterface] | None,
    resolved_signature_namespace: dict[str, Any],
    resolved_type_encoders: TypeEncodersMap,
) -> None:
    listener_context.listener_callback_signature = listener_callback_signature = ParsedSignature.from_fn(
        listener_context.listener_callback, resolved_signature_namespace
    )

    if "data" not in listener_callback_signature.parameters:
        raise ImproperlyConfiguredException("Websocket listeners must accept a 'data' parameter")

    for param in ("request", "body"):
        if param in listener_callback_signature.parameters:
            raise ImproperlyConfiguredException(f"The {param} kwarg is not supported with websocket listeners")

    listener_context.can_send_data = not listener_callback_signature.return_type.is_subclass_of(NoneType)
    listener_context.pass_socket = "socket" in listener_callback_signature.parameters
    listener_context.resolved_data_dto = resolved_data_dto
    listener_context.resolved_return_dto = resolved_return_dto
    listener_context.handle_receive = _create_handle_receive(
        resolved_data_dto, receive_mode, listener_callback_signature.parameters["data"].annotation
    )
    should_encode_to_json = not (
        listener_callback_signature.return_type.is_subclass_of((str, bytes))
        or (
            listener_callback_signature.return_type.is_optional
            and listener_callback_signature.return_type.has_inner_subclass_of((str, bytes))
        )
    )
    json_encoder = JsonEncoder(enc_hook=partial(default_serializer, type_encoders=resolved_type_encoders))
    listener_context.handle_send = _create_handle_send(
        resolved_return_dto, json_encoder, should_encode_to_json, send_mode
    )
