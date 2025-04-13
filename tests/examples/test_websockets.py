from datetime import datetime

from docs.examples.websockets.custom_websocket import app as custom_websocket_class_app
from docs.examples.websockets.stream_and_receive_listener import app
from time_machine import travel

from litestar.testing import AsyncTestClient
from litestar.testing.client.sync_client import TestClient


def test_custom_websocket_class():
    client = TestClient(app=custom_websocket_class_app)

    with client.websocket_connect("/") as ws:
        ws.send({"data": "I should not be in response"})
        data = ws.receive()
        assert data["text"] == "Fixed response"


@travel(datetime.datetime.now(datetime.UTC), tick=False)
async def test_websocket_listener() -> None:
    """Test the websocket listener."""
    async with AsyncTestClient(app) as client:
        with await client.websocket_connect("/") as ws:
            ws.send_text("Hello")
            data = ws.receive_text()
            assert data == datetime.datetime.now(datetime.UTC).isoformat()
            data = ws.receive_text()
            assert data == "Hello"


async def test_websocket_handler():
    pass
