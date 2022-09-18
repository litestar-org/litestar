"""The tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_websockets.py
"""

from typing import TYPE_CHECKING

import anyio
import pytest
from starlette import status
from starlette.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from starlite import WebSocketException
from starlite.connection import WebSocket

if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


def test_websocket_url():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        await websocket.send_json({"url": str(websocket.url)})
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/123?a=abc") as websocket:
        data = websocket.receive_json()
        assert data == {"url": "ws://testserver/123?a=abc"}


def test_websocket_binary_json():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        message = await websocket.receive_json(mode="binary")
        await websocket.send_json(message, mode="binary")
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/123?a=abc") as websocket:
        websocket.send_json({"test": "data"}, mode="binary")
        data = websocket.receive_json(mode="binary")
        assert data == {"test": "data"}


def test_websocket_query_params():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        query_params = dict(websocket.query_params)
        await websocket.accept()
        await websocket.send_json({"params": query_params})
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/?a=abc&b=456") as websocket:
        data = websocket.receive_json()
        assert data == {"params": {"a": ["abc"], "b": ["456"]}}


def test_websocket_headers():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        headers = dict(websocket.headers)
        await websocket.accept()
        await websocket.send_json({"headers": headers})
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        expected_headers = {
            "accept": "*/*",
            "accept-encoding": "gzip, deflate, br",
            "connection": "upgrade",
            "host": "testserver",
            "user-agent": "testclient",
            "sec-websocket-key": "testserver==",
            "sec-websocket-version": "13",
        }
        data = websocket.receive_json()
        assert data == {"headers": expected_headers}


def test_websocket_port():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        await websocket.send_json({"port": websocket.url.port})
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("ws://example.com:123/123?a=abc") as websocket:
        data = websocket.receive_json()
        assert data == {"port": 123}


def test_websocket_send_and_receive_text():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        data = await websocket.receive_text()
        await websocket.send_text("Message was: " + data)
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        websocket.send_text("Hello, world!")
        data = websocket.receive_text()
        assert data == "Message was: Hello, world!"


def test_websocket_send_and_receive_bytes():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        data = await websocket.receive_bytes()
        await websocket.send_bytes(b"Message was: " + data)
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        websocket.send_bytes(b"Hello, world!")
        data = websocket.receive_bytes()
        assert data == b"Message was: Hello, world!"


def test_websocket_send_and_receive_json():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        data = await websocket.receive_json()
        await websocket.send_json({"message": data})
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        websocket.send_json({"hello": "world"})
        data = websocket.receive_json()
        assert data == {"message": {"hello": "world"}}


def test_websocket_concurrency_pattern():
    stream_send, stream_receive = anyio.create_memory_object_stream()

    async def reader(websocket):
        async with stream_send:
            data = await websocket.receive_json()
            await stream_send.send(data)

    async def writer(websocket):
        async with stream_receive:
            async for message in stream_receive:
                await websocket.send_json(message)

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        async with anyio.create_task_group() as task_group:
            task_group.start_soon(reader, websocket)
            await writer(websocket)
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        websocket.send_json({"hello": "world"})
        data = websocket.receive_json()
        assert data == {"hello": "world"}


def test_client_close():
    close_code = None

    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        nonlocal close_code
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        try:
            await websocket.receive_text()
        except WebSocketException as exc:
            close_code = exc.code

    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        websocket.close(code=status.WS_1001_GOING_AWAY)
    assert close_code == status.WS_1001_GOING_AWAY


def test_application_close():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        await websocket.close(status.WS_1001_GOING_AWAY)

    client = TestClient(app)
    with client.websocket_connect("/") as websocket, pytest.raises(WebSocketDisconnect) as exc:
        websocket.receive_text()
    assert exc.value.code == status.WS_1001_GOING_AWAY


def test_rejected_connection():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.close(status.WS_1001_GOING_AWAY)

    client = TestClient(app)
    with pytest.raises(WebSocketDisconnect) as exc, client.websocket_connect("/"):
        pass  # pragma: nocover
    assert exc.value.code == status.WS_1001_GOING_AWAY


def test_subprotocol():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        assert websocket.scope["subprotocols"] == ["soap", "wamp"]
        await websocket.accept(subprotocols="wamp")
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/", subprotocols=["soap", "wamp"]) as websocket:
        assert websocket.accepted_subprotocol == "wamp"


def test_additional_headers():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept(headers=[(b"additional", b"header")])
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        assert websocket.extra_headers == [(b"additional", b"header")]


def test_no_additional_headers():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        await websocket.close()

    client = TestClient(app)
    with client.websocket_connect("/") as websocket:
        assert websocket.extra_headers == []


def test_websocket_exception():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        raise RuntimeError

    client = TestClient(app)
    with pytest.raises(RuntimeError), client.websocket_connect("/123?a=abc"):
        pass  # pragma: nocover


def test_duplicate_disconnect():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        message = await websocket.receive()
        assert message["type"] == "websocket.disconnect"
        message = await websocket.receive()

    client = TestClient(app)
    with pytest.raises(WebSocketException), client.websocket_connect("/") as websocket:
        websocket.close()


def test_websocket_close_reason() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.accept()
        await websocket.close(code=status.WS_1001_GOING_AWAY, reason="Going Away")

    client = TestClient(app)
    with client.websocket_connect("/") as websocket, pytest.raises(WebSocketDisconnect) as exc:
        websocket.receive_text()
        assert exc.value.code == status.WS_1001_GOING_AWAY
        assert exc.value.reason == "Going Away"


def test_receive_text_before_accept():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.receive_text()

    client = TestClient(app)
    with pytest.raises(WebSocketException), client.websocket_connect("/"):
        pass  # pragma: nocover


def test_receive_bytes_before_accept():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.receive_bytes()

    client = TestClient(app)
    with pytest.raises(WebSocketException), client.websocket_connect("/"):
        pass  # pragma: nocover


def test_receive_json_before_accept():
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        websocket = WebSocket(scope, receive=receive, send=send)
        await websocket.receive_json()

    client = TestClient(app)
    with pytest.raises(WebSocketException), client.websocket_connect("/"):
        pass  # pragma: nocover
