from http import HTTPStatus

from litestar import Litestar, route
from litestar.config.cors import CORSConfig
from litestar.enums import HttpMethod
from litestar.response import Response
from litestar.testing import TestClient


@route("/custom-options", http_method=HttpMethod.OPTIONS)
async def custom_options_handler() -> Response[str]:
    return Response(
        status_code=200,
        headers={"Custom-Handler": "Active"},
        content="Handled by Custom Options",
    )


cors_config = CORSConfig(allow_methods=["GET", "OPTIONS"], allow_origins=["https://allowed-origin.com"])
app = Litestar(route_handlers=[custom_options_handler], cors_config=cors_config)


def test_custom_options_handler_cors_pre_flight_request() -> None:
    with TestClient(app) as client:
        response = client.options(
            "/custom-options", headers={"Origin": "https://allowed-origin.com", "Access-Control-Request-Method": "GET"}
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert "access-control-allow-origin" in response.headers
        assert "Custom-Handler" not in response.headers


def test_custom_options_handler_non_cors_request() -> None:
    with TestClient(app) as client:
        response = client.options("/custom-options")
        assert response.status_code == 200
        assert response.headers.get("Custom-Handler") == "Active"
        assert response.text == "Handled by Custom Options"
