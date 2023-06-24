from docs.examples.middleware.base import app

from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient


def test_base_middleware_example_websocket() -> None:
    with TestClient(app).websocket_connect("/my-websocket") as ws:
        assert b"x-process-time" not in dict(ws.scope["headers"])


def test_exclude_by_regex() -> None:
    with TestClient(app) as client:
        response = client.get("first_path")
        assert response.status_code == HTTP_200_OK
        assert "x-process-time" not in response.headers
        response = client.get("second_path")
        assert response.status_code == HTTP_200_OK
        assert "x-process-time" not in response.headers


def test_exclude_by_opt_key() -> None:
    with TestClient(app) as client:
        response = client.get("third_path")
        assert response.status_code == HTTP_200_OK
        assert "x-process-time" not in response.headers


def test_not_excluded() -> None:
    with TestClient(app) as client:
        response = client.get("/greet")
        assert response.status_code == HTTP_200_OK
        assert "x-process-time" in response.headers
