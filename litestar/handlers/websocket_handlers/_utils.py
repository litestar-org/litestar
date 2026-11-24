from __future__ import annotations

from functools import wraps
from inspect import Parameter, Signature
from typing import TYPE_CHECKING, Any

from msgspec.json import Encoder as JsonEncoder

from litestar.di import NamedDependency, Provider
from litestar.serialization import decode_json
from litestar.types.builtin_types import NoneType
from litestar.utils import ensure_async_callable
from litestar.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine

    from litestar import WebSocket
    from litestar.handlers.websocket_handlers.listener import WebsocketListenerRouteHandler
    from litestar.types import AnyCallable
    from litestar.utils.signature import ParsedSignature


def create_handle_receive(listener: WebsocketListenerRouteHandler) -> Callable[[WebSocket], Coroutine[Any, None, None]]:
    if (plan := listener._dto_plan) is None and listener.data_dto is not None:
        listener._raise_not_registered()

    if plan is not None and (decode_bytes := plan.decode_bytes) is not None:

        async def handle_receive(socket: WebSocket) -> Any:
            received_data = await socket.receive_data(mode=listener._receive_mode)
            return decode_bytes(
                received_data.encode("utf-8") if isinstance(received_data, str) else received_data, socket
            )

    elif listener.parsed_data_field and listener.parsed_data_field.annotation is str:

        async def handle_receive(socket: WebSocket) -> Any:
            received_data = await socket.receive_data(mode=listener._receive_mode)
            return received_data.decode("utf-8") if isinstance(received_data, bytes) else received_data

    elif listener.parsed_data_field and listener.parsed_data_field.annotation is bytes:

        async def handle_receive(socket: WebSocket) -> Any:
            received_data = await socket.receive_data(mode=listener._receive_mode)
            return received_data.encode("utf-8") if isinstance(received_data, str) else received_data

    else:

        async def handle_receive(socket: WebSocket) -> Any:
            received_data = await socket.receive_data(mode=listener._receive_mode)
            return decode_json(value=received_data, type_decoders=socket.route_handler.type_decoders)

    return handle_receive


def create_handle_send(
    listener: WebsocketListenerRouteHandler,
) -> Callable[[WebSocket, Any], Coroutine[None, None, None]]:
    json_encoder = JsonEncoder(enc_hook=listener.default_serializer)

    if (plan := listener._dto_plan) is None and listener.return_dto is not None:
        listener._raise_not_registered()

    if plan is not None and (encode := plan.encode) is not None:
        skip_none = plan.return_ is not None and plan.return_.backend._passes_none

        async def handle_send(socket: WebSocket, data: Any) -> None:
            if data is None and skip_none:
                return
            data = json_encoder.encode(encode(data))
            await socket.send_data(data=data, mode=listener._send_mode)

    elif listener.parsed_return_field.is_subclass_of((str, bytes)) or (
        listener.parsed_return_field.is_optional and listener.parsed_return_field.has_inner_subclass_of((str, bytes))
    ):

        async def handle_send(socket: WebSocket, data: Any) -> None:
            if data is not None:
                await socket.send_data(data=data, mode=listener._send_mode)

    else:

        async def handle_send(socket: WebSocket, data: Any) -> None:
            if data is not None:
                data = json_encoder.encode(data)
                await socket.send_data(data=data, mode=listener._send_mode)

    return handle_send


class ListenerHandler:
    __slots__ = ("_can_send_data", "_fn", "_listener", "_pass_socket", "_wrapped_fn")

    def __init__(
        self,
        listener: WebsocketListenerRouteHandler,
        fn: AnyCallable,
        parsed_signature: ParsedSignature,
        namespace: dict[str, Any],
    ) -> None:
        self._can_send_data = not parsed_signature.return_type.is_subclass_of(NoneType)
        self._wrapped_fn = fn
        self._fn = ensure_async_callable(fn)
        self._listener = listener
        self._pass_socket = "socket" in parsed_signature.parameters

    async def __call__(
        self,
        *args: Any,
        socket: WebSocket,
        connection_lifespan_dependencies: NamedDependency[dict[str, Any]],
        **kwargs: Any,
    ) -> None:
        lifespan_manager = self._listener._connection_lifespan or self._listener.default_connection_lifespan
        handle_send = self._listener.resolve_send_handler() if self._can_send_data else None
        handle_receive = self._listener.resolve_receive_handler()

        if self._pass_socket:
            kwargs["socket"] = socket

        async with lifespan_manager(**connection_lifespan_dependencies):
            while True:
                received_data = await handle_receive(socket)
                data = await self._fn(*args, data=received_data, **kwargs)
                if handle_send:
                    await handle_send(socket, data)


def create_handler_signature(callback_signature: Signature) -> Signature:
    """Create the :class:`Signature` a listener's dependencies are read from: the callback's without
    ``data``, with ``socket`` if the callback does not declare it, and with
    ``connection_lifespan_dependencies``.

    Args:
        callback_signature: The :class:`Signature` of the listener callback.

    Returns:
        The :class:`Signature` of the listener's handler.
    """
    new_params = [p for p in callback_signature.parameters.values() if p.name != "data"]
    if "socket" not in callback_signature.parameters:
        new_params.append(Parameter(name="socket", kind=Parameter.KEYWORD_ONLY, annotation="WebSocket"))

    new_params.append(
        Parameter(
            name="connection_lifespan_dependencies",
            kind=Parameter.KEYWORD_ONLY,
            annotation="NamedDependency[Dict[str, Any]]",
        )
    )

    return callback_signature.replace(parameters=new_params)


def create_stub_dependency(src: AnyCallable | None, key: str) -> Provider:
    """Create a provider under ``key`` of the kwargs defined in ``src``, or of ``None`` without ``src``"""
    if src is None:

        async def empty_stub() -> None:
            return None

        return Provider(empty_stub, key=key)

    src = unwrap_partial(src)

    @wraps(src)
    async def stub(**kwargs: Any) -> dict[str, Any]:
        return kwargs

    return Provider(stub, key=key)
