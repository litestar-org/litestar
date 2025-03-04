from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.status_codes import HTTP_204_NO_CONTENT
from litestar.testing import TestClient


@get("/credentials-test")
async def credentials_handler() -> str:
    return "Test Successful!"


def test_cors_with_credentials_allowed() -> None:
    cors_config = CORSConfig(
        allow_methods=["GET"], allow_origins=["https://allowed-origin.com"], allow_credentials=True
    )
    app = Litestar(route_handlers=[credentials_handler], cors_config=cors_config)

    with TestClient(app) as client:
        response = client.options(
            "/endpoint", headers={"Origin": "https://allowed-origin.com", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_with_credentials_disallowed() -> None:
    cors_config = CORSConfig(
        allow_methods=["GET"],
        allow_origins=["https://allowed-origin.com"],
        allow_credentials=False,  # Credentials should not be allowed
    )
    app = Litestar(route_handlers=[credentials_handler], cors_config=cors_config)

    with TestClient(app) as client:
        response = client.options(
            "/endpoint", headers={"Origin": "https://allowed-origin.com", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == HTTP_204_NO_CONTENT
        assert "access-control-allow-credentials" not in response.headers
