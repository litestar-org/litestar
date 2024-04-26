from __future__ import annotations

from typing import TYPE_CHECKING

from litestar import Litestar, asgi, get
from litestar.enums import ScopeType
from litestar.testing import TestClient

if TYPE_CHECKING:
    from litestar.types.asgi_types import Receive, Scope, Send


async def asgi_app(scope: Scope, receive: Receive, send: Send) -> None:
    assert scope["type"] == ScopeType.HTTP
    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                (b"content-type", b"text/plain"),
                (b"content-length", b"%d" % len(scope["raw_path"])),
            ],
        }
    )
    await send(
        {
            "type": "http.response.body",
            "body": scope["raw_path"],
            "more_body": False,
        }
    )


asgi_handler = asgi("/", is_mount=True)(asgi_app)


@get("/path")
async def get_handler() -> str:
    return "Hello, world!"


app = Litestar(
    route_handlers=[asgi_handler, get_handler],
    openapi_config=None,
    debug=True,
)


def test_regular_handler_under_mounted_asgi_app() -> None:
    # https://github.com/litestar-org/litestar/issues/3429
    with TestClient(app) as client:
        resp = client.get("/some/path")
        assert resp.content == b"/some/path"
