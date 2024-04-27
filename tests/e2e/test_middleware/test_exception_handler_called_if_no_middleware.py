"""Test exception handlers defined on layers are called for middleware exceptions."""

from __future__ import annotations

from unittest.mock import MagicMock

from litestar import get
from litestar.connection import Request
from litestar.response import Response
from litestar.testing import create_test_client

exception_handler_mock = MagicMock()


def exception_handler(_: Request, __: type[Exception]) -> Response:
    exception_handler_mock()
    return Response(content="", status_code=500)


@get("/raising", sync_to_thread=False)
def raising() -> None:
    raise RuntimeError("damn")


def test_middleware_send_wrapper_called_on_exception() -> None:
    with create_test_client(
        [raising], exception_handlers={RuntimeError: exception_handler}, openapi_config=None
    ) as client:
        client.get("/raising")
        exception_handler_mock.assert_called_once()
