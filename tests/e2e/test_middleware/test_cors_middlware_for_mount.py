from __future__ import annotations

from http import HTTPStatus
from unittest.mock import MagicMock

from litestar import Litestar, asgi
from litestar.config.cors import CORSConfig
from litestar.enums import ScopeType
from litestar.testing import TestClient
from litestar.types.asgi_types import Receive, Scope, Send

asgi_mock = MagicMock()


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


cors_config = CORSConfig(allow_methods=["*"], allow_origins=["https://some-domain.com"])
app = Litestar(
    cors_config=cors_config,
    route_handlers=[
        asgi("/app", is_mount=True)(asgi_app),
    ],
    openapi_config=None,
)


def test_cors_middleware_for_mount() -> None:
    with TestClient(app) as client:
        response = client.options(
            "http://127.0.0.1:8000/app",
            headers={"origin": "https://some-domain.com"},
        )
        assert response.status_code == HTTPStatus.NO_CONTENT
        assert response.headers["access-control-allow-origin"] == "https://some-domain.com"
    asgi_mock.assert_not_called()
