"""A large part of the tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_responses.py And are
meant to ensure our compatibility with their API.
"""
from typing import TYPE_CHECKING

import pytest
import responses  # type: ignore

from starlite import ImproperlyConfiguredException, Response, Starlite, get
from starlite.response import RedirectResponse
from starlite.status_codes import HTTP_200_OK, HTTP_301_MOVED_PERMANENTLY
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

    client = TestClient(app)
    response = client.get("/redirect")
    assert response.text == "hello, world"
    assert response.url == "http://testserver/"


@pytest.mark.xfail
@responses.activate
def test_external_redirect_response() -> None:
    external_url = "https://example.com"
    content = "external redirect"

    @get(path="/first")
    def first() -> RedirectResponse:
        return RedirectResponse(url=external_url)

    @get(path="/last")
    def last() -> str:
        return content

    app = Starlite(route_handlers=[first, last])

    client = TestClient(app)
    responses.add(
        responses.Response(
            responses.GET,
            url=external_url,
            status=HTTP_301_MOVED_PERMANENTLY,
            headers={"Location": f"{client.base_url}/last"},
            auto_calculate_content_length=True,
        )
    )
    response = client.get("/first", follow_redirects=True)

    assert response.text == content


def test_quoting_redirect_response() -> None:
    async def app(scope: "Scope", receive: "Receive", send: "Send") -> None:
        if scope["path"] == "/test/":
            response = Response("hello, world", media_type="text/plain")
        else:
            response = RedirectResponse(url="/test/")
        await response(scope, receive, send)

    client = TestClient(app)
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

    client: TestClient = TestClient(app)
    response = client.request("GET", "/redirect", follow_redirects=False)
    assert str(response.url) == "http://testserver/redirect"
    assert "content-length" not in response.headers


def test_redirect_response_status_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        RedirectResponse("/", status_code=HTTP_200_OK)  # type: ignore
