from __future__ import annotations

from queue import Empty
from typing import TYPE_CHECKING, Any, Callable, NoReturn

import pytest

from litestar import Controller, Litestar, WebSocket, delete, get, head, patch, post, put, websocket
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from litestar.testing import TestClient, WebSocketTestSession, create_test_client

if TYPE_CHECKING:
    from litestar.types import (
        AnyIOBackend,
        HTTPResponseBodyEvent,
        HTTPResponseStartEvent,
        Receive,
        Scope,
        Send,
    )


def test_use_testclient_in_endpoint(test_client_backend: AnyIOBackend) -> None:
    """this test is taken from starlette."""

    @get("/")
    def mock_service_endpoint() -> dict:
        return {"mock": "example"}

    mock_service = Litestar(route_handlers=[mock_service_endpoint])

    @get("/")
    def homepage() -> Any:
        client = TestClient(mock_service, backend=test_client_backend)
        response = client.get("/")
        return response.json()

    app = Litestar(route_handlers=[homepage])

    client = TestClient(app)
    response = client.get("/")
    assert response.json() == {"mock": "example"}


def raise_error() -> NoReturn:
    raise RuntimeError()


def test_error_handling_on_startup(test_client_backend: AnyIOBackend) -> None:
    with pytest.raises(RuntimeError), TestClient(Litestar(on_startup=[raise_error]), backend=test_client_backend):
        pass


def test_error_handling_on_shutdown(test_client_backend: AnyIOBackend) -> None:
    with pytest.raises(RuntimeError), TestClient(Litestar(on_shutdown=[raise_error]), backend=test_client_backend):
        pass


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete", "head", "options"])
def test_client_interface(method: str, test_client_backend: AnyIOBackend) -> None:
    async def asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
        start_event: HTTPResponseStartEvent = {
            "type": "http.response.start",
            "status": HTTP_200_OK,
            "headers": [(b"content-type", b"text/plain")],
        }
        await send(start_event)
        body_event: HTTPResponseBodyEvent = {"type": "http.response.body", "body": b"", "more_body": False}
        await send(body_event)

    client = TestClient(asgi_app, backend=test_client_backend)
    if method == "get":
        response = client.get("/")
    elif method == "post":
        response = client.post("/")
    elif method == "put":
        response = client.put("/")
    elif method == "patch":
        response = client.patch("/")
    elif method == "delete":
        response = client.delete("/")
    elif method == "head":
        response = client.head("/")
    else:
        response = client.options("/")
    assert response.status_code == HTTP_200_OK


async def mock_asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
    pass


def test_warns_problematic_domain() -> None:
    with pytest.warns(UserWarning):
        TestClient(app=mock_asgi_app, base_url="http://testserver")


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete", "head", "options"])
def test_client_interface_context_manager(method: str, test_client_backend: AnyIOBackend) -> None:
    class MockController(Controller):
        @get("/")
        def mock_service_endpoint_get(self) -> dict:
            return {"mock": "example"}

        @post("/")
        def mock_service_endpoint_post(self) -> dict:
            return {"mock": "example"}

        @put("/")
        def mock_service_endpoint_put(self) -> None:
            ...

        @patch("/")
        def mock_service_endpoint_patch(self) -> None:
            ...

        @delete("/")
        def mock_service_endpoint_delete(self) -> None:
            ...

        @head("/")
        def mock_service_endpoint_head(self) -> None:
            ...

    mock_service = Litestar(route_handlers=[MockController])
    with TestClient(mock_service, backend=test_client_backend) as client:
        if method == "get":
            response = client.get("/")
            assert response.status_code == HTTP_200_OK
        elif method == "post":
            response = client.post("/")
            assert response.status_code == HTTP_201_CREATED
        elif method == "put":
            response = client.put("/")
            assert response.status_code == HTTP_200_OK
        elif method == "patch":
            response = client.patch("/")
            assert response.status_code == HTTP_200_OK
        elif method == "delete":
            response = client.delete("/")
            assert response.status_code == HTTP_204_NO_CONTENT
        elif method == "head":
            response = client.head("/")
            assert response.status_code == HTTP_200_OK
        else:
            response = client.options("/")
            assert response.status_code == HTTP_204_NO_CONTENT


@pytest.mark.parametrize("block,timeout", [(False, None), (False, 0.001), (True, 0.001)])
@pytest.mark.parametrize(
    "receive_method",
    [
        WebSocketTestSession.receive,
        WebSocketTestSession.receive_json,
        WebSocketTestSession.receive_text,
        WebSocketTestSession.receive_bytes,
    ],
)
def test_websocket_test_session_block_timeout(
    receive_method: Callable[..., Any], block: bool, timeout: float | None, anyio_backend: AnyIOBackend
) -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.accept()

    with pytest.raises(Empty):
        with create_test_client(handler, backend=anyio_backend) as client, client.websocket_connect("/") as ws:
            receive_method(ws, timeout=timeout, block=block)
