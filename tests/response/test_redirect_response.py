"""A large part of the tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_responses.py And are meant to ensure our compatibility with
their API.
"""
from typing import TYPE_CHECKING

import pytest

from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.base import ASGIResponse
from litestar.response.redirect import ASGIRedirectResponse
from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient

if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send


def test_redirect_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = ASGIResponse(body=b"hello, world", media_type="text/plain")
        else:
            response = ASGIRedirectResponse(url="/")
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/redirect")
    assert response.text == "hello, world"
    assert response.url == "http://testserver.local/"


def test_quoting_redirect_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/test/":
            response = ASGIResponse(body=b"hello, world", media_type="text/plain")
        else:
            response = ASGIRedirectResponse(url="/test/")
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/redirect", follow_redirects=True)
    assert response.text == "hello, world"
    assert str(response.url) == "http://testserver.local/test/"


def test_redirect_response_content_length_header() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = ASGIResponse(body=b"hello", media_type="text/plain")
        else:
            response = ASGIRedirectResponse(url="/")
        await response(scope, receive, send)

    client: TestClient = TestClient(app)
    response = client.request("GET", "/redirect", follow_redirects=False)
    assert str(response.url) == "http://testserver.local/redirect"
    assert "content-length" not in response.headers


def test_redirect_response_status_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ASGIRedirectResponse(url="/", status_code=HTTP_200_OK)  # type:ignore[arg-type]


def test_redirect_response_html_media_type() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = ASGIResponse(body=b"hello")
        else:
            response = ASGIRedirectResponse(url="/", media_type="text/html")
        await response(scope, receive, send)

    client: TestClient = TestClient(app)
    response = client.request("GET", "/redirect", follow_redirects=False)
    assert str(response.url) == "http://testserver.local/redirect"
    assert "text/html" in str(response.headers["Content-Type"])


def test_redirect_response_media_type_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ASGIRedirectResponse(url="/", media_type="application/json")
