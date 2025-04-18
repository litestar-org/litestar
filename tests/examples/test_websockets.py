from docs.examples.websockets.custom_websocket import app as custom_websocket_class_app
from docs.examples.websockets.stream_and_receive_listener import app as app_stream_and_receive_listener
from docs.examples.websockets.stream_and_receive_raw import app as app_stream_and_receive_raw

from litestar.testing import AsyncTestClient
from litestar.testing.client.sync_client import TestClient


def test_custom_websocket_class():
    client = TestClient(app=custom_websocket_class_app)

    with client.websocket_connect("/") as ws:
        ws.send({"data": "I should not be in response"})
        data = ws.receive()
        assert data["text"] == "Fixed response"


async def test_websocket_listener() -> None:
    """Test the websocket listener."""
    async with AsyncTestClient(app_stream_and_receive_listener) as client:
        with await client.websocket_connect("/") as ws:
            ws.send_text("Hello")
            data_1 = ws.receive_text()
            data_2 = ws.receive_text()
            assert sorted([data_1, data_2]) == sorted(["Hello", "ping"])


async def test_websocket_handler():
    async with AsyncTestClient(app_stream_and_receive_raw) as client:
        with await client.websocket_connect("/") as ws:
            echo_data = {"data": "I should be in response"}
            ws.send_json(echo_data)
            assert ws.receive_json(timeout=0.5) == {"handle_receive": "start"}
            assert ws.receive_json(timeout=0.5) == echo_data
            assert ws.receive_text(timeout=0.5)
