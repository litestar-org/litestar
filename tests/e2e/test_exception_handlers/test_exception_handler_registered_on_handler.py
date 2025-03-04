# ruff: noqa: UP006
from __future__ import annotations

from unittest.mock import MagicMock

from litestar import Request, Response, get
from litestar.testing import create_test_client

mock = MagicMock()


def value_error_handler(_: Request, exc: ValueError) -> Response:
    mock()
    return Response({"error": str(exc)}, status_code=500)


@get("/", exception_handlers={ValueError: value_error_handler})
async def home() -> None:
    raise ValueError("Something went wrong")


def test_exception_handler_registered_on_handler() -> None:
    with create_test_client([home]) as client:
        response = client.get("/")
        assert response.status_code == 500
        assert response.json() == {"error": "Something went wrong"}

    mock.assert_called_once()
