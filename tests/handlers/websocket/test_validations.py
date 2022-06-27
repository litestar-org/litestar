from typing import Any

import pytest

from starlite import ImproperlyConfiguredException, WebSocket, websocket
from starlite.testing import create_test_client


def test_websocket_handler_function_validation() -> None:
    def fn_without_socket_arg(websocket: WebSocket) -> None:
        pass

    with pytest.raises(ImproperlyConfiguredException):
        websocket(path="/")(fn_without_socket_arg)  # type: ignore

    def fn_with_return_annotation(socket: WebSocket) -> dict:
        return dict()

    with pytest.raises(ImproperlyConfiguredException):
        websocket(path="/")(fn_with_return_annotation)  # type: ignore

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

        @websocket(path="/")  # type: ignore
        def sync_websocket_handler(socket: WebSocket) -> None:
            ...
