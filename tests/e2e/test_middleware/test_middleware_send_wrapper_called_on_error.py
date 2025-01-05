"""Test middleware send_wrapper called on exception."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock

from litestar import get
from litestar.exceptions import InternalServerException
from litestar.testing import create_test_client

if TYPE_CHECKING:
    from litestar.types.asgi_types import ASGIApp, Message, Receive, Scope, Send

mock = MagicMock()


def asgi_middleware(app: ASGIApp) -> ASGIApp:
    async def middleware(scope: Scope, receive: Receive, send: Send) -> None:
        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                mock(message["type"], message["status"])
            await send(message)

        await app(scope, receive, send_wrapper)

    return middleware


@get("/raising", sync_to_thread=False)
def raising() -> None:
    raise InternalServerException("This is an exception")


def test_middleware_send_wrapper_called_on_exception() -> None:
    with create_test_client([raising], middleware=[asgi_middleware]) as client:
        client.get("/raising")
        mock.assert_called_once_with("http.response.start", 500)
