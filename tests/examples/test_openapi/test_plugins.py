import pytest

from litestar.testing import TestClient


def test_rapidoc_simple() -> None:
    from docs.examples.openapi.plugins.rapidoc_simple import app

    with TestClient(app=app) as client:
        resp = client.get("/schema/rapidoc")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert "Litestar Example" in resp.text


def test_redoc_simple() -> None:
    from docs.examples.openapi.plugins.redoc_simple import app

    with TestClient(app=app) as client:
        resp = client.get("/schema/redoc")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert "Litestar Example" in resp.text


def test_stoplights_simple() -> None:
    from docs.examples.openapi.plugins.stoplight_simple import app

    with TestClient(app=app) as client:
        resp = client.get("/schema/elements")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert "Litestar Example" in resp.text


def test_swagger_ui_simple() -> None:
    from docs.examples.openapi.plugins.swagger_ui_simple import app

    with TestClient(app=app) as client:
        resp = client.get("/schema/swagger")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert "Litestar Example" in resp.text


@pytest.mark.parametrize("path", ["/schema/openapi.yml", "/schema/openapi.yaml"])
def test_yaml_simple(path: str) -> None:
    from docs.examples.openapi.plugins.yaml_simple import app

    with TestClient(app=app) as client:
        resp = client.get(path)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/vnd.oai.openapi"
        assert "Litestar Example" in resp.text


def test_serving_multiple_uis() -> None:
    from docs.examples.openapi.plugins.serving_multiple_uis import app

    with TestClient(app=app) as client:
        resp = client.get("/schema/rapidoc")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert "Litestar Example" in resp.text

        resp = client.get("/schema/swagger")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/html; charset=utf-8"
        assert "Litestar Example" in resp.text
