from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.status_codes import HTTP_204_NO_CONTENT
from litestar.testing import TestClient


@get("/handler")
async def handler() -> str:
    return "Handler"


def test_non_cors_options_request_no_origin_header() -> None:
    cors_config = CORSConfig(
        allow_methods=["PUT"],
        allow_origins=["https://specific-domain.com"],
    )
    app = Litestar(route_handlers=[handler], cors_config=cors_config)

    with TestClient(app) as client:
        # Request without an 'Origin' header
        response = client.options("/handler")
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.headers["allow"] == "GET, OPTIONS"


def test_non_cors_options_no_config() -> None:
    app = Litestar(route_handlers=[handler])

    with TestClient(app) as client:
        # Request with an origin that does not require CORS handling
        response = client.options("/handler", headers={"Origin": "https://not-configured-origin.com"})
        assert response.status_code == HTTP_204_NO_CONTENT
        assert response.headers["allow"] == "GET, OPTIONS"
