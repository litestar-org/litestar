# ruff: noqa: UP006
from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from litestar import Request, Response, asgi
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send

mock = MagicMock()


def value_error_handler(_: Request, exc: ValueError) -> Response:
    mock()
    return Response({"error": str(exc)}, status_code=500)


@asgi("/mount", exception_handlers={ValueError: value_error_handler})
async def mounted(scope: Scope, receive: Receive, send: Send) -> None:
    raise ValueError("Something went wrong")


def test_exception_handler_registered_on_handler() -> None:
    with create_test_client([mounted]) as client:
        response = client.get("/mount")
        assert response.status_code == 500
        assert response.json() == {"error": "Something went wrong"}

    mock.assert_called_once()
