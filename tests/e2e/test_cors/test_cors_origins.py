from http import HTTPStatus

from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.testing import TestClient


@get("/endpoint")
async def handler() -> str:
    return "Hello, world!"


cors_config = CORSConfig(
    allow_methods=["GET"], allow_origins=["https://allowed-origin.com", "https://another-allowed-origin.com"]
)
app = Litestar(route_handlers=[handler], cors_config=cors_config)


def test_cors_with_allowed_origins() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/custom-options", headers={"Origin": "https://allowed-origin.com", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.headers["access-control-allow-origin"] == "https://allowed-origin.com"

        response = client.options(
            "/custom-options",
            headers={"Origin": "https://another-allowed-origin.com", "Access-Control-Request-Method": "GET"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.headers["access-control-allow-origin"] == "https://another-allowed-origin.com"


def test_cors_with_disallowed_origin() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/custom-options",
            headers={"Origin": "https://disallowed-origin.com", "Access-Control-Request-Method": "GET"},
        )
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert "access-control-allow-origin" not in response.headers
