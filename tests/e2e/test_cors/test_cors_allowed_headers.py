from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.status_codes import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST
from litestar.testing import TestClient


@get("/headers-test")
async def headers_handler() -> str:
    return "Test Successful!"


cors_config = CORSConfig(
    allow_methods=["GET"],
    allow_origins=["https://allowed-origin.com"],
    allow_headers=["X-Custom-Header", "Content-Type"],
)
app = Litestar(route_handlers=[headers_handler], cors_config=cors_config)


def test_cors_with_specific_allowed_headers() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/endpoint",
            headers={
                "Origin": "https://allowed-origin.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Custom-Header, Content-Type",
            },
        )
        assert response.status_code == HTTP_204_NO_CONTENT
        assert "x-custom-header" in response.headers["access-control-allow-headers"]
        assert "content-type" in response.headers["access-control-allow-headers"]


def test_cors_with_unauthorized_headers() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/endpoint",
            headers={
                "Origin": "https://allowed-origin.com",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Not-Allowed-Header",
            },
        )
        assert response.status_code == HTTP_400_BAD_REQUEST
        assert (
            "access-control-allow-headers" not in response.headers
            or "x-not-allowed-header" not in response.headers.get("access-control-allow-headers", "")
        )
