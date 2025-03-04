from http import HTTPStatus

from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.testing import TestClient


@get("/method-test")
async def method_handler() -> str:
    return "Method Test Successful!"


cors_config = CORSConfig(allow_methods=["GET", "POST"], allow_origins=["https://allowed-origin.com"])
app = Litestar(route_handlers=[method_handler], cors_config=cors_config)


def test_cors_allowed_methods() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/method-test", headers={"Origin": "https://allowed-origin.com", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.headers["access-control-allow-origin"] == "https://allowed-origin.com"
        assert "GET" in response.headers["access-control-allow-methods"]

        response = client.options(
            "/method-test", headers={"Origin": "https://allowed-origin.com", "Access-Control-Request-Method": "POST"}
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert "POST" in response.headers["access-control-allow-methods"]


def test_cors_disallowed_methods() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/method-test", headers={"Origin": "https://allowed-origin.com", "Access-Control-Request-Method": "PUT"}
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "PUT" not in response.headers.get("access-control-allow-methods", "")
