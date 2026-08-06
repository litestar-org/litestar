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


def test_cors_credentials_with_wildcard_origin_echoes_specific_origin() -> None:
    """A literal "*" can't be combined with credentials - browsers reject the response
    outright (Fetch spec) - so when both are configured, the request's own Origin must
    be echoed back on both the preflight and the actual response, never "*".
    """
    cors_config = CORSConfig(allow_methods=["GET"], allow_credentials=True)  # allow_origins defaults to ["*"]
    app = Litestar(route_handlers=[credentials_handler], cors_config=cors_config)

    with TestClient(app) as client:
        preflight = client.options(
            "/credentials-test",
            headers={"Origin": "https://example.com", "Access-Control-Request-Method": "GET"},
        )
        assert preflight.status_code == HTTP_204_NO_CONTENT
        assert preflight.headers["access-control-allow-origin"] == "https://example.com"
        assert preflight.headers["access-control-allow-credentials"] == "true"

        # No Cookie header present - e.g. the first request of a session - must still
        # get a valid, credentials-compatible response.
        response = client.get("/credentials-test", headers={"Origin": "https://example.com"})
        assert response.headers["access-control-allow-origin"] == "https://example.com"
        assert response.headers["access-control-allow-credentials"] == "true"
