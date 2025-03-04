"""Test exception handlers defined on layers are called for middleware exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from litestar import get
from litestar.connection import Request
from litestar.response import Response
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.types.asgi_types import ASGIApp, Receive, Scope, Send

exception_handler_mock = MagicMock()
route_handler_mock = MagicMock()


def exception_handler(_: Request, __: type[Exception]) -> Response:
    exception_handler_mock()
    return Response(content="", status_code=500)


def asgi_middleware(app: ASGIApp) -> ASGIApp:
    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        raise RuntimeError("damn")

    return middleware


@get("/not_called", exception_handlers={RuntimeError: exception_handler}, sync_to_thread=False)
def not_called() -> None:
    route_handler_mock()


def test_middleware_send_wrapper_called_on_exception() -> None:
    with create_test_client([not_called], middleware=[asgi_middleware], openapi_config=None) as client:
        client.get("/not_called")
        route_handler_mock.assert_not_called()
        exception_handler_mock.assert_called_once()
