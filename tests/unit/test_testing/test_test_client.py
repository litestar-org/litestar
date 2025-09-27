import asyncio
import contextlib
from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING, Callable, NoReturn, cast

import anyio
from _pytest.fixtures import FixtureRequest

from litestar import Controller, Request, WebSocket, delete, head, patch, put, websocket
from litestar.middleware.session.base import BaseBackendConfig
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_204_NO_CONTENT
from litestar.stores.base import Store
from litestar.testing import AsyncTestClient, WebSocketTestSession, create_async_test_client, create_test_client
from litestar.testing.websocket_test_session import AsyncWebSocketTestSession

if TYPE_CHECKING:
    from litestar.types import (
        AnyIOBackend,
        Receive,
        Scope,
        Send,
    )

from typing import Any

import pytest

from litestar import Litestar, get, post
from litestar.testing import TestClient
from litestar.utils.helpers import get_exception_group

_ExceptionGroup = get_exception_group()

AnyTestClient = TestClient | AsyncTestClient


async def mock_asgi_app(scope: "Scope", receive: "Receive", send: "Send") -> None:
    pass


@pytest.fixture(params=[AsyncTestClient, TestClient])
def test_client_cls(request: FixtureRequest) -> type[AnyTestClient]:
    return cast(type[AnyTestClient], request.param)


@pytest.mark.parametrize("anyio_backend", ["asyncio", "trio"])
def test_test_client_get_set_session_data_no_backend(anyio_backend: "AnyIOBackend") -> None:
    with create_test_client(backend=anyio_backend) as client:
        with pytest.raises(RuntimeError, match="Session backend not configured"):
            client.set_session_data({})

        with pytest.raises(RuntimeError, match="Session backend not configured"):
            client.get_session_data()


async def test_test_client_get_set_session_data_no_backend_async() -> None:
    async with create_async_test_client() as client:
        with pytest.RaisesExc(RuntimeError, match="Session backend not configured"):
            await client.set_session_data({})

        with pytest.RaisesExc(RuntimeError, match="Session backend not configured"):
            await client.get_session_data()


@pytest.mark.parametrize("anyio_backend", ["asyncio", "trio"])
@pytest.mark.parametrize("with_domain", [False, True])
def test_test_client_set_session_data(
    with_domain: bool,
    anyio_backend: str,
    session_backend_config: "BaseBackendConfig",
    test_client_backend: "AnyIOBackend",
) -> None:
    session_data = {"foo": "bar"}

    if with_domain:
        session_backend_config.domain = "testserver.local"

    @get(path="/test")
    async def get_session_data(request: Request) -> dict[str, Any]:
        return request.session

    app = Litestar(route_handlers=[get_session_data], middleware=[session_backend_config.middleware])

    with TestClient(app=app, session_config=session_backend_config, backend=test_client_backend) as client:
        client.set_session_data(session_data)
        assert client.get("/test").json() == session_data


@pytest.mark.parametrize(
    "anyio_backend",
    [
        pytest.param("asyncio"),
        pytest.param("trio", marks=pytest.mark.xfail(reason="Known issue with trio backend", strict=False)),
    ],
)
@pytest.mark.parametrize("with_domain", [True, False])
def test_test_client_get_session_data(
    with_domain: bool,
    anyio_backend: str,
    session_backend_config: "BaseBackendConfig",
    test_client_backend: "AnyIOBackend",
    store: Store,
) -> None:
    session_data = {"foo": "bar"}

    if with_domain:
        session_backend_config.domain = "testserver.local"

    @post(path="/test")
    async def set_session_data(request: Request) -> None:
        request.session.update(session_data)

    app = Litestar(
        route_handlers=[set_session_data], middleware=[session_backend_config.middleware], stores={"session": store}
    )

    with TestClient(app=app, session_config=session_backend_config, backend=test_client_backend) as client:
        client.post("/test")
        assert client.get_session_data() == session_data


@pytest.mark.parametrize("with_domain", [False, True])
async def test_test_client_set_session_data_async(
    with_domain: bool,
    session_backend_config: "BaseBackendConfig",
) -> None:
    session_data = {"foo": "bar"}

    if with_domain:
        session_backend_config.domain = "testserver.local"

    @get(path="/test")
    async def get_session_data(request: Request) -> dict[str, Any]:
        return request.session

    app = Litestar(route_handlers=[get_session_data], middleware=[session_backend_config.middleware])

    async with AsyncTestClient(app=app, session_config=session_backend_config) as client:
        await client.set_session_data(session_data)
        assert (await client.get("/test")).json() == session_data


@pytest.mark.parametrize("with_domain", [True, False])
async def test_test_client_get_session_data_async(
    with_domain: bool,
    session_backend_config: "BaseBackendConfig",
    store: Store,
) -> None:
    session_data = {"foo": "bar"}

    if with_domain:
        session_backend_config.domain = "testserver.local"

    @post(path="/test")
    async def set_session_data(request: Request) -> None:
        request.session.update(session_data)

    app = Litestar(
        route_handlers=[set_session_data], middleware=[session_backend_config.middleware], stores={"session": store}
    )

    async with AsyncTestClient(app=app, session_config=session_backend_config) as client:
        await client.post("/test")
        assert await client.get_session_data() == session_data


async def test_use_testclient_in_endpoint(
    test_client_backend: "AnyIOBackend", test_client_cls: type[AnyTestClient]
) -> None:
    """this test is taken from starlette."""

    @get("/")
    def mock_service_endpoint() -> dict:
        return {"mock": "example"}

    mock_service = Litestar(route_handlers=[mock_service_endpoint])

    @get("/async")
    async def endpoint_async() -> Any:
        async with AsyncTestClient(mock_service) as c:
            local_response = await c.get("/")
            return local_response.json()

    @get("/sync")
    async def endpoint_sync() -> Any:
        with TestClient(mock_service) as c:
            local_response = c.get("/")
            return local_response.json()

    app = Litestar(route_handlers=[endpoint_async, endpoint_sync])

    async with AsyncTestClient(app) as client:
        response_async = await client.get("/async")
        response_sync = await client.get("/sync")
        assert response_async.json() == {"mock": "example"}
        assert response_sync.json() == {"mock": "example"}


def raise_error(app: Litestar) -> NoReturn:
    raise RuntimeError()


async def test_error_handling_on_startup_async() -> None:
    with pytest.raises(_ExceptionGroup):
        async with AsyncTestClient(Litestar(on_startup=[raise_error])):
            pass


def test_error_handling_on_startup(test_client_backend: "AnyIOBackend") -> None:
    with pytest.raises(_ExceptionGroup):
        with TestClient(Litestar(on_startup=[raise_error]), backend=test_client_backend):
            pass


def test_error_handling_on_shutdown(test_client_backend: "AnyIOBackend") -> None:
    with pytest.raises(_ExceptionGroup):
        with TestClient(Litestar(on_shutdown=[raise_error]), backend=test_client_backend):
            pass


async def test_error_handling_on_shutdown_async() -> None:
    with pytest.raises(_ExceptionGroup):
        async with AsyncTestClient(Litestar(on_shutdown=[raise_error])):
            pass


def test_warns_problematic_domain(test_client_cls: type[AnyTestClient]) -> None:
    with pytest.warns(UserWarning):
        test_client_cls(app=mock_asgi_app, base_url="http://testserver")


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete", "head", "options"])
async def test_client_interface_context_manager(
    method: str, test_client_backend: "AnyIOBackend", test_client_cls: type[AnyTestClient]
) -> None:
    class MockController(Controller):
        @get("/")
        def mock_service_endpoint_get(self) -> dict:
            return {"mock": "example"}

        @post("/")
        def mock_service_endpoint_post(self) -> dict:
            return {"mock": "example"}

        @put("/")
        def mock_service_endpoint_put(self) -> None: ...

        @patch("/")
        def mock_service_endpoint_patch(self) -> None: ...

        @delete("/")
        def mock_service_endpoint_delete(self) -> None: ...

        @head("/")
        def mock_service_endpoint_head(self) -> None: ...

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


@pytest.mark.parametrize("method", ["get", "post", "put", "patch", "delete", "head", "options"])
async def test_client_interface_context_manager_async(method: str) -> None:
    class MockController(Controller):
        @get("/")
        def mock_service_endpoint_get(self) -> dict:
            return {"mock": "example"}

        @post("/")
        def mock_service_endpoint_post(self) -> dict:
            return {"mock": "example"}

        @put("/")
        def mock_service_endpoint_put(self) -> None: ...

        @patch("/")
        def mock_service_endpoint_patch(self) -> None: ...

        @delete("/")
        def mock_service_endpoint_delete(self) -> None: ...

        @head("/")
        def mock_service_endpoint_head(self) -> None: ...

    mock_service = Litestar(route_handlers=[MockController])
    async with AsyncTestClient(mock_service) as client:
        if method == "get":
            response = await client.get("/")
            assert response.status_code == HTTP_200_OK
        elif method == "post":
            response = await client.post("/")
            assert response.status_code == HTTP_201_CREATED
        elif method == "put":
            response = await client.put("/")
            assert response.status_code == HTTP_200_OK
        elif method == "patch":
            response = await client.patch("/")
            assert response.status_code == HTTP_200_OK
        elif method == "delete":
            response = await client.delete("/")
            assert response.status_code == HTTP_204_NO_CONTENT
        elif method == "head":
            response = await client.head("/")
            assert response.status_code == HTTP_200_OK
        else:
            response = await client.options("/")
            assert response.status_code == HTTP_204_NO_CONTENT


@pytest.mark.parametrize("block,exception", [(True, TimeoutError), (False, anyio.WouldBlock)])
@pytest.mark.parametrize(
    "receive_method",
    [
        WebSocketTestSession.receive,
        WebSocketTestSession.receive_json,
        WebSocketTestSession.receive_text,
        WebSocketTestSession.receive_bytes,
    ],
)
def test_websocket_receive_no_data_with_timeout(
    receive_method: Callable[..., Any], block: bool, exception: type[Exception]
) -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.accept()

    with (
        create_test_client(handler) as client,
        client.websocket_connect("/") as ws,
    ):
        with pytest.raises(exception):
            receive_method(ws, timeout=0.01, block=block)


@pytest.mark.parametrize(
    "receive_method",
    [
        WebSocketTestSession.receive,
        WebSocketTestSession.receive_json,
        WebSocketTestSession.receive_text,
        WebSocketTestSession.receive_bytes,
    ],
)
def test_websocket_receive_no_data_no_timeout_no_block(receive_method: Callable[..., Any]) -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.accept()

    with create_test_client(handler) as client, client.websocket_connect("/") as ws:
        with pytest.raises(anyio.WouldBlock):
            receive_method(ws, timeout=None, block=False)


def test_websocket_accept_timeout(anyio_backend: "AnyIOBackend") -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        pass

    with create_test_client(handler, backend=anyio_backend) as client:
        with pytest.RaisesGroup(pytest.RaisesExc(TimeoutError)):
            with client.websocket_connect("/", timeout=0.1):
                pass


def test_unexpected_message_before_accept(anyio_backend: "AnyIOBackend") -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.send({"type": "something.else"})  # type: ignore[typeddict-item]

    with create_test_client(handler, backend=anyio_backend) as client:
        with pytest.RaisesGroup(
            pytest.RaisesExc(RuntimeError, match=r"Unexpected ASGI message.*Received 'something\.else'")
        ):
            with client.websocket_connect("/"):
                pass


def test_websocket_connect(anyio_backend: "AnyIOBackend") -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.accept()
        data = await socket.receive_json()
        await socket.send_json(data)
        await socket.close()

    with create_test_client(handler, backend=anyio_backend, timeout=0.1) as client:
        with client.websocket_connect("/", subprotocols="wamp") as ws:
            ws.send_json({"data": "123"})
            data = ws.receive_json()
            assert data == {"data": "123"}


# ASYNC TESTS
@pytest.mark.parametrize("block,exception", [(True, TimeoutError), (False, anyio.WouldBlock)])
@pytest.mark.parametrize(
    "receive_method",
    [
        AsyncWebSocketTestSession.receive,
        AsyncWebSocketTestSession.receive_json,
        AsyncWebSocketTestSession.receive_text,
        AsyncWebSocketTestSession.receive_bytes,
    ],
)
async def test_websocket_receive_no_data_with_timeout_async(
    receive_method: Callable[..., Any], block: bool, exception: type[Exception]
) -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.accept()

    async with (
        create_async_test_client(handler) as client,
        await client.websocket_connect("/") as ws,
    ):
        with pytest.raises(exception):
            await receive_method(ws, timeout=0.01, block=block)


@pytest.mark.parametrize(
    "receive_method",
    [
        AsyncWebSocketTestSession.receive,
        AsyncWebSocketTestSession.receive_json,
        AsyncWebSocketTestSession.receive_text,
        AsyncWebSocketTestSession.receive_bytes,
    ],
)
async def test_websocket_receive_no_data_no_timeout_no_block_async(receive_method: Callable[..., Any]) -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.accept()

    async with create_async_test_client(handler) as client, await client.websocket_connect("/") as ws:
        with pytest.raises(anyio.WouldBlock):
            await receive_method(ws, timeout=None, block=False)


async def test_websocket_accept_timeout_async() -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        pass

    async with create_async_test_client(handler) as client:
        with pytest.raises(TimeoutError):
            async with await client.websocket_connect("/", timeout=0.1):
                pass


async def test_websocket_accept_no_timeout_async() -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        pass

    async with create_async_test_client(handler) as client:
        with pytest.raises(TimeoutError), anyio.fail_after(0.01):
            async with await client.websocket_connect("/"):
                pass


async def test_unexpected_message_before_accept_async() -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.send({"type": "something.else"})  # type: ignore[typeddict-item]

    async with create_async_test_client(handler) as client:
        with pytest.raises(RuntimeError, match=r"Unexpected ASGI message.*Received 'something\.else'"):
            async with await client.websocket_connect("/"):
                pass


async def test_websocket_connect_async() -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.accept()
        data = await socket.receive_json()
        await socket.send_json(data)
        await socket.close()

    async with create_async_test_client(handler, timeout=0.1) as client:
        async with await client.websocket_connect("/", subprotocols="wamp") as ws:
            await ws.send_json({"data": "123"})
            data = await ws.receive_json()
            assert data == {"data": "123"}


def test_websocket_send_msgpack() -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.accept()
        msg = await socket.receive_msgpack()
        await socket.send_msgpack(msg)
        await socket.close()

    with create_test_client(handler) as client, client.websocket_connect("/") as ws:
        data = {"hello": "world"}
        ws.send_msgpack(data)
        assert ws.receive_msgpack(timeout=0.1) == data


async def test_websocket_send_msgpack_async() -> None:
    @websocket()
    async def handler(socket: WebSocket) -> None:
        await socket.accept()
        msg = await socket.receive_msgpack()
        await socket.send_msgpack(msg)
        await socket.close()

    async with create_async_test_client(handler) as client, await client.websocket_connect("/") as ws:
        data = {"hello": "world"}
        await ws.send_msgpack(data)
        assert await ws.receive_msgpack(timeout=0.1) == data


async def test_client_uses_native_loop() -> None:
    @get("/")
    def handler() -> dict:
        return {"loop_id": id(asyncio.get_running_loop())}

    async with create_async_test_client(handler) as client:
        res = await client.get("/")
    assert res.json() == {"loop_id": id(asyncio.get_running_loop())}


async def test_lifespan_uses_native_loop() -> None:
    @contextlib.asynccontextmanager
    async def lifespan(app: Litestar) -> AsyncGenerator[None, None]:
        app.state["loop"] = asyncio.get_running_loop()
        yield

    async with create_async_test_client([], lifespan=[lifespan]) as client:
        assert client.app.state["loop"] is asyncio.get_running_loop()
