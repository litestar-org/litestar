"""A large part of the tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_responses.py And are meant to ensure our compatibility with
their API.
"""
from typing import TYPE_CHECKING

import pytest

from litestar import Response
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response import RedirectResponse
from litestar.status_codes import HTTP_200_OK, HTTP_307_TEMPORARY_REDIRECT
from litestar.testing import TestClient

if TYPE_CHECKING:
    from litestar.types import Receive, Scope, Send


def test_redirect_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = Response("hello, world", media_type="text/plain").to_asgi_response()
        else:
            response = RedirectResponse("/").to_asgi_response()
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/redirect")
    assert response.text == "hello, world"
    assert response.url == "http://testserver.local/"


def test_quoting_redirect_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/test/":
            response = Response("hello, world", media_type="text/plain").to_asgi_response()
        else:
            response = RedirectResponse(url="/test/").to_asgi_response()
        await response(scope, receive, send)

    client = TestClient(app)
    response = client.get("/redirect", follow_redirects=True)
    assert response.text == "hello, world"
    assert str(response.url) == "http://testserver.local/test/"


def test_redirect_response_content_length_header() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = Response("hello", media_type="text/plain").to_asgi_response()
        else:
            response = RedirectResponse("/").to_asgi_response()
        await response(scope, receive, send)

    client: TestClient = TestClient(app)
    response = client.request("GET", "/redirect", follow_redirects=False)
    assert str(response.url) == "http://testserver.local/redirect"
    assert "content-length" not in response.headers


def test_redirect_response_status_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        RedirectResponse("/", status_code=HTTP_200_OK).to_asgi_response()  # type:ignore[arg-type]


def test_redirect_response_html_media_type() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/":
            response = Response("hello").to_asgi_response()
        else:
            response = RedirectResponse("/", media_type="text/html").to_asgi_response()
        await response(scope, receive, send)

    client: TestClient = TestClient(app)
    response = client.request("GET", "/redirect", follow_redirects=False)
    assert str(response.url) == "http://testserver.local/redirect"
    assert "text/html" in str(response.headers["Content-Type"])


def test_redirect_response_media_type_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        RedirectResponse("/", status_code=HTTP_307_TEMPORARY_REDIRECT, media_type="application/json").to_asgi_response()
