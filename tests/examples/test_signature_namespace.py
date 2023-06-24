from docs.examples.signature_namespace.app import app

from litestar.testing import TestClient


def test_msgpack_app() -> None:
    test_data = {"a": 1, "b": "two"}

    with TestClient(app=app) as client:
        response = client.post("/", json=test_data)
        assert response.json() == test_data
