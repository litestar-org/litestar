import pytest
from starlette.requests import HTTPConnection
from starlette.status import HTTP_200_OK, HTTP_403_FORBIDDEN
from starlette.types import Receive, Scope, Send
from starlette.websockets import WebSocketDisconnect

from starlite import (
    BaseRouteHandler,
    MediaType,
    Request,
    Response,
    asgi,
    get,
    websocket,
)
from starlite.connection import WebSocket
from starlite.exceptions import PermissionDeniedException
from starlite.testing import create_test_client


async def local_guard(_: HTTPConnection, route_handler: BaseRouteHandler) -> None:
    if not route_handler.opt or not route_handler.opt.get("allow_all"):
        raise PermissionDeniedException("local")


def app_guard(request: Request, _: BaseRouteHandler) -> None:
    if not request.headers.get("Authorization"):
        raise PermissionDeniedException("app")


def test_guards_with_http_handler() -> None:
    @get(path="/secret", guards=[local_guard])
    def my_http_route_handler() -> None:
        ...

    with create_test_client(guards=[app_guard], route_handlers=[my_http_route_handler]) as client:
        response = client.get("/secret")
        assert response.status_code == HTTP_403_FORBIDDEN
        assert response.json().get("detail") == "app"
        response = client.get("/secret", headers={"Authorization": "yes"})
        assert response.status_code == HTTP_403_FORBIDDEN
        assert response.json().get("detail") == "local"
        my_http_route_handler.opt["allow_all"] = True
        response = client.get("/secret", headers={"Authorization": "yes"})
        assert response.status_code == HTTP_200_OK


def test_guards_with_asgi_handler() -> None:
    @asgi(path="/secret", guards=[local_guard])
    async def my_asgi_handler(scope: Scope, receive: Receive, send: Send) -> None:
        response = Response(media_type=MediaType.JSON, status_code=HTTP_200_OK, content={"hello": "world"})
        await response(scope=scope, receive=receive, send=send)

    with create_test_client(guards=[app_guard], route_handlers=[my_asgi_handler]) as client:
        response = client.get("/secret")
        assert response.status_code == HTTP_403_FORBIDDEN
        assert response.json().get("detail") == "app"
        response = client.get("/secret", headers={"Authorization": "yes"})
        assert response.status_code == HTTP_403_FORBIDDEN
        assert response.json().get("detail") == "local"
        my_asgi_handler.opt["allow_all"] = True
        response = client.get("/secret", headers={"Authorization": "yes"})
        assert response.status_code == HTTP_200_OK


def test_guards_with_websocket_handler() -> None:
    @websocket(path="/", guards=[local_guard])
    async def my_websocket_route_handler(socket: WebSocket) -> None:
        await socket.accept()
        data = await socket.receive_json()
        assert data
        await socket.send_json({"data": "123"})
        await socket.close()

    client = create_test_client(route_handlers=my_websocket_route_handler)

    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/") as ws:
        ws.send_json({"data": "123"})

    my_websocket_route_handler.opt["allow_all"] = True

    with client.websocket_connect("/") as ws:
        ws.send_json({"data": "123"})
