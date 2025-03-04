from __future__ import annotations

from http import HTTPStatus
from unittest.mock import MagicMock

import pytest

from litestar import Litestar, asgi
from litestar.config.cors import CORSConfig
from litestar.enums import ScopeType
from litestar.testing import TestClient
from litestar.types.asgi_types import ASGIApp, Receive, Scope, Send


@pytest.fixture(name="asgi_mock")
def asgi_mock_fixture() -> MagicMock:
    return MagicMock()


@pytest.fixture(name="asgi_app")
def asgi_app_fixture(asgi_mock: MagicMock) -> ASGIApp:
    async def asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
        asgi_mock()

        assert scope["type"] == ScopeType.HTTP

        while True:
            event = await receive()
            if event["type"] == "http.request" and not event.get("more_body", False):
                break

        await send(
            {
                "type": "http.response.start",
                "status": 200,
                "headers": [
                    (b"content-type", b"text/plain"),
                ],
            }
        )

        await send(
            {
                "type": "http.response.body",
                "body": b"Hello, world!",
                "more_body": False,
            }
        )

    return asgi_app


def test_cors_middleware_for_mount(asgi_app: ASGIApp, asgi_mock: MagicMock) -> None:
    cors_config = CORSConfig(allow_methods=["*"], allow_origins=["https://some-domain.com"])
    app = Litestar(
        cors_config=cors_config,
        route_handlers=[
            asgi("/app", is_mount=True)(asgi_app),
        ],
        openapi_config=None,
    )

    with TestClient(app) as client:
        response = client.options(
            "http://127.0.0.1:8000/app",
            headers={"origin": "https://some-domain.com"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.headers["access-control-allow-origin"] == "https://some-domain.com"
    asgi_mock.assert_not_called()


def test_asgi_app_no_origin_header(asgi_app: ASGIApp, asgi_mock: MagicMock) -> None:
    cors_config = CORSConfig(allow_methods=["*"], allow_origins=["https://some-domain.com"])
    app = Litestar(
        cors_config=cors_config,
        route_handlers=[
            asgi("/app", is_mount=True)(asgi_app),
        ],
        openapi_config=None,
    )

    with TestClient(app) as client:
        response = client.options("http://127.0.0.1/app")
        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "text/plain"
        asgi_mock.assert_called()


def test_asgi_app_without_cors_configuration(asgi_app: ASGIApp, asgi_mock: MagicMock) -> None:
    non_cors_app = Litestar(
        route_handlers=[asgi("/app", is_mount=True)(asgi_app)],
        openapi_config=None,
    )

    with TestClient(non_cors_app) as client:
        response = client.options("http://127.0.0.1:8000/app")
        assert response.status_code == HTTPStatus.OK
        assert response.headers["content-type"] == "text/plain"
        asgi_mock.assert_called()
