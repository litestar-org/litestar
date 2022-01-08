import pytest
from pydantic import BaseModel
from starlette.requests import HTTPConnection
from starlette.status import HTTP_200_OK, HTTP_403_FORBIDDEN
from starlette.websockets import WebSocketDisconnect

from starlite import Starlite, create_test_client, get, websocket
from starlite.exceptions import PermissionDeniedException
from starlite.middleware import AbstractAuthenticationMiddleware, AuthenticationResult
from starlite.request import Request, WebSocket


class User(BaseModel):
    name: str
    id: int


class Auth(BaseModel):
    props: str


user = User(name="moishe", id=100)
auth = Auth(props="abc")

state = {}


class AuthMiddleware(AbstractAuthenticationMiddleware):
    async def authenticate_request(self, request: HTTPConnection) -> AuthenticationResult:
        param = request.headers.get("Authorization")
        if param in state:
            return state.pop(param)
        raise PermissionDeniedException("unauthenticated")


@get(path="/")
def http_route_handler(request: Request[User, Auth]) -> None:
    assert isinstance(request.user, User)
    assert isinstance(request.auth, Auth)
    return None


def test_authentication_middleware_http_routes():
    client = create_test_client(route_handlers=[http_route_handler], middleware=[AuthMiddleware])
    token = "abc"
    error_response = client.get("/", headers={"Authorization": token})
    assert error_response.status_code == HTTP_403_FORBIDDEN
    state[token] = AuthenticationResult(user=user, auth=auth)
    success_response = client.get("/", headers={"Authorization": token})
    assert success_response.status_code == HTTP_200_OK


@websocket(path="/")
async def websocket_route_handler(socket: WebSocket[User, Auth]) -> None:
    await socket.accept()
    assert isinstance(socket.user, User)
    assert isinstance(socket.auth, Auth)
    assert isinstance(socket.app, Starlite)
    await socket.send_json({"data": "123"})
    await socket.close()


def test_authentication_middleware_websocket_routes():
    token = "abc"
    client = create_test_client(route_handlers=websocket_route_handler, middleware=[AuthMiddleware])
    with pytest.raises(WebSocketDisconnect), client.websocket_connect("/", headers={"Authorization": token}) as ws:
        assert ws.receive_json()
    state[token] = AuthenticationResult(user=user, auth=auth)
    with client.websocket_connect("/", headers={"Authorization": token}) as ws:
        assert ws.receive_json()
