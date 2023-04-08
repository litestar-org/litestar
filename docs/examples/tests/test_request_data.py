from examples.request_data.msgpack_request import app as msgpack_app
from litestar.serialization import encode_msgpack
from litestar.testing import TestClient


def test_msgpack_app() -> None:
    test_data = {"name": "Moishe Zuchmir", "age": 30, "programmer": True}

    with TestClient(app=msgpack_app) as client:
        response = client.post("/", content=encode_msgpack(test_data))
        assert response.json() == test_data
