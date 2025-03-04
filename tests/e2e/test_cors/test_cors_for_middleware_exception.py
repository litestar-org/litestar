from http import HTTPStatus

from litestar import Litestar, get
from litestar.config.cors import CORSConfig
from litestar.exceptions import HTTPException
from litestar.middleware import AbstractMiddleware
from litestar.testing import TestClient
from litestar.types.asgi_types import Receive, Scope, Send


class ExceptionMiddleware(AbstractMiddleware):
    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        raise HTTPException(status_code=HTTPStatus.INTERNAL_SERVER_ERROR, detail="Intentional Error")


@get("/test")
async def handler() -> str:
    return "Should not reach this"


cors_config = CORSConfig(allow_methods=["GET"], allow_origins=["https://allowed-origin.com"], allow_credentials=True)
app = Litestar(route_handlers=[handler], cors_config=cors_config, middleware=[ExceptionMiddleware])


def test_cors_on_middleware_exception() -> None:
    with TestClient(app) as client:
        response = client.get("/test", headers={"Origin": "https://allowed-origin.com"})
        assert response.status_code == HTTPStatus.INTERNAL_SERVER_ERROR
        assert response.headers["access-control-allow-origin"] == "https://allowed-origin.com"
        assert response.headers["access-control-allow-credentials"] == "true"
