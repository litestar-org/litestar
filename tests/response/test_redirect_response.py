"""The tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_responses.py And are
meant to ensure our compatibility with their API.
"""
from typing import TYPE_CHECKING

from starlite import Response
from starlite.response import RedirectResponse
from starlite.testing import TestClient

if TYPE_CHECKING:
    from starlite.types import Receive, Scope, Send


def test_redirect_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = Response("hello, world", media_type="text/plain")
        else:
            response = RedirectResponse("/")
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/redirect")
    assert response.text == "hello, world"
    assert response.url == "http://testserver/"


def test_quoting_redirect_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/test/":
            response = Response("hello, world", media_type="text/plain")
        else:
            response = RedirectResponse(url="/test/")
        await response(scope, receive, send)

    client = TestClient(app)  # type: ignore
    response = client.get("/redirect", follow_redirects=True)
    assert response.text == "hello, world"
    assert str(response.url) == "http://testserver/test/"


def test_redirect_response_content_length_header() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = Response("hello", media_type="text/plain")  # pragma: nocover
        else:
            response = RedirectResponse("/")
        await response(scope, receive, send)

    client: TestClient = TestClient(app)  # type: ignore
    response = client.request("GET", "/redirect", follow_redirects=False)
    assert response.url == "http://testserver/redirect"
    assert "content-length" not in response.headers
