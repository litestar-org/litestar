"""A large part of the tests in this file were adapted from:

https://github.com/encode/starlette/blob/master/tests/test_responses.py And are meant to ensure our compatibility with
their API.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from litestar import get
from litestar.datastructures import MultiDict
from litestar.exceptions import ImproperlyConfiguredException
from litestar.response.redirect import ASGIRedirectResponse, Redirect
from litestar.status_codes import HTTP_200_OK
from litestar.testing import create_test_client

if TYPE_CHECKING:
    pass


def test_redirect_response() -> None:
    @get("/redirect")
    def redirect() -> Redirect:
        return Redirect(path="/")

    @get("/")
    def index() -> str:
        return "hello, world"

    with create_test_client([redirect, index], raise_server_exceptions=True) as client:
        response = client.get("/redirect")
        assert response.text == "hello, world"
        assert response.url == "http://testserver.local/"
        assert "content-length" in response.headers


def test_redirect_response_status_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ASGIRedirectResponse(path="/", status_code=HTTP_200_OK)  # type:ignore[arg-type]


def test_redirect_response_html_media_type() -> None:
    @get("/redirect")
    def redirect() -> Redirect:
        return Redirect(path="/", media_type="text/html")

    @get("/")
    def index() -> str:
        return "hello"

    with create_test_client([index, redirect]) as client:
        response = client.request("GET", "/redirect", follow_redirects=False)
        assert str(response.url) == "http://testserver.local/redirect"
        assert "text/html" in str(response.headers["Content-Type"])


def test_redirect_response_media_type_validation() -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ASGIRedirectResponse(path="/", media_type="application/mspgpack")


@pytest.mark.parametrize(
    "status_code,expected_status_code",
    [
        (301, 301),
        (302, 302),
        (303, 303),
        (307, 307),
        (308, 308),
    ],
)
def test_redirect_dynamic_status_code(status_code: int | None, expected_status_code: int) -> None:
    @get("/")
    def handler() -> Redirect:
        return Redirect(path="/something-else", status_code=status_code)  # type: ignore[arg-type]

    with create_test_client(
        [handler],
    ) as client:
        res = client.get("/", follow_redirects=False)
        assert res.status_code == expected_status_code


@pytest.mark.parametrize(
    "query_params", [{"single": "a", "list": ["b", "c"]}, MultiDict([("single", "a"), ("list", "b"), ("list", "c")])]
)
def test_redirect_with_query_params(query_params: dict[str, str | list[str]] | MultiDict) -> None:
    @get("/")
    def handler() -> Redirect:
        return Redirect(path="/something-else", query_params=query_params)

    with create_test_client([handler]) as client:
        location_header = client.get("/", follow_redirects=False).headers["location"]
        expected = "/something-else?single=a&list=b&list=c"
        assert location_header == expected


@pytest.mark.parametrize("handler_status_code", [301, 307, None])
def test_redirect(handler_status_code: int | None) -> None:
    @get("/", status_code=handler_status_code)
    def handler() -> Redirect:
        return Redirect(path="/something-else", status_code=handler_status_code)  # type: ignore[arg-type]

    with create_test_client([handler]) as client:
        res = client.get("/", follow_redirects=False)
        assert res.status_code == 302 if handler_status_code is None else handler_status_code
