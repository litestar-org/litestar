from typing import Any

import pytest

from starlite import (
    ImproperlyConfiguredException,
    WebSocket,
    create_test_client,
    websocket,
)


def test_websocket_handler_function_validation():
    def fn_without_socket_arg(websocket: WebSocket) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        websocket(path="/")(fn_without_socket_arg)

    def fn_with_return_annotation(socket: WebSocket) -> dict:
        return dict()

    with pytest.raises(ImproperlyConfiguredException):
        websocket(path="/")(fn_with_return_annotation)

    websocket_handler_with_no_fn = websocket(path="/")

    with pytest.raises(ImproperlyConfiguredException):
        create_test_client(route_handlers=websocket_handler_with_no_fn)

    with pytest.raises(ImproperlyConfiguredException):

        @websocket(path="/")
        async def websocket_handler_with_data_kwarg(socket: WebSocket, data: Any) -> None:
            ...

    with pytest.raises(ImproperlyConfiguredException):

        @websocket(path="/")
        async def websocket_handler_with_request_kwarg(socket: WebSocket, request: Any) -> None:
            ...

    with pytest.raises(ImproperlyConfiguredException):

        @websocket(path="/")
        def sync_websocket_handler(socket: WebSocket) -> None:
            ...
