from http import HTTPStatus

from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.testing import TestClient


@get("/test")
async def handler() -> str:
    return "Should not reach this"


cors_config = CORSConfig(allow_methods=["GET"], allow_origins=["https://allowed-origin.com"], allow_credentials=True)
app = Litestar(route_handlers=[handler], cors_config=cors_config)


def test_cors_on_middleware_exception_with_origin_header() -> None:
    with TestClient(app) as client:
        response = client.get("/testing", headers={"Origin": "https://allowed-origin.com"})
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.headers["access-control-allow-origin"] == "https://allowed-origin.com"
        assert response.headers["access-control-allow-credentials"] == "true"
