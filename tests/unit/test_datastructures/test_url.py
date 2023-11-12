from typing import TYPE_CHECKING, Callable

import pytest

from litestar.datastructures import MultiDict
from litestar.datastructures.url import URL, make_absolute_url

if TYPE_CHECKING:
    from litestar.types import Scope


@pytest.mark.parametrize(
    "base,path",
    [
        ("http://example.org", "foo/bar?param=value&param2=value2"),
        ("http://example.org/", "foo/bar?param=value&param2=value2"),
        ("http://example.org", "/foo/bar?param=value&param2=value2"),
        ("http://example.org/", "/foo/bar?param=value&param2=value2"),
    ],
)
def test_make_absolute_url(path: str, base: str) -> None:
    result = "http://example.org/foo/bar?param=value&param2=value2"
    assert make_absolute_url(path, base) == result


def test_url() -> None:
    url = URL("https://foo:hunter2@example.org:81/bar/baz?query=param&bool=true#fragment")
    assert url.scheme == "https"
    assert url.netloc == "foo:hunter2@example.org:81"
    assert url.path == "/bar/baz"
    assert url.query == "query=param&bool=true"
    assert url.fragment == "fragment"
    assert url.username == "foo"
    assert url.password == "hunter2"
    assert url.port == 81
    assert url.hostname == "example.org"
    assert url.query_params.dict() == {"query": ["param"], "bool": ["true"]}


@pytest.mark.parametrize(
    "component,value",
    [
        ("scheme", "https"),
        ("netloc", "example.org"),
        ("path", "/foo/bar"),
        ("query", "foo=bar"),
        ("fragment", "anchor"),
    ],
)
def test_url_from_components(component: str, value: str) -> None:
    expected = {"scheme": "", "netloc": "", "path": "", "query": "", "fragment": "", component: value}
    url = URL.from_components(**{component: value})
    for key, value in expected.items():
        assert getattr(url, key) == value


@pytest.mark.parametrize(
    "component,replacement,expected",
    [
        ("scheme", "http", "http"),
        ("netloc", "example.com", "example.com"),
        ("path", "/foo", "/foo"),
        ("query", None, ""),
        ("query", "", ""),
        ("query", MultiDict({}), ""),
        ("query", "foo=baz", "foo=baz"),
        ("query", MultiDict({"foo": "baz"}), "foo=baz"),
        ("fragment", "anchor2", "anchor2"),
    ],
)
def test_url_with_replacements(component: str, replacement: str, expected: str) -> None:
    defaults = {
        "scheme": "https",
        "netloc": "example.org",
        "path": "/foo/bar",
        "query": "foo=bar",
        "fragment": "anchor",
    }
    url = URL.from_components(**defaults)
    defaults[component] = expected
    url = url.with_replacements(**{component: replacement})
    for key, value in defaults.items():
        assert getattr(url, key) == value


def test_url_from_scope(create_scope: Callable[..., "Scope"]) -> None:
    scope = create_scope(
        scheme="https",
        server=("testserver.local", 70),
        root_path="/foo",
        path="/bar",
        query_string="bar=baz",
        headers=[],
    )

    url = URL.from_scope(scope)

    assert url.scheme == "https"
    assert url.netloc == "testserver.local:70"
    assert url.path == "/foo/bar"
    assert url.query == "bar=baz"


def test_url_from_scope_with_host(create_scope: Callable[..., "Scope"]) -> None:
    scope = create_scope(headers=[(b"host", b"testserver.local:42")])

    url = URL.from_scope(scope)

    assert url.netloc == "testserver.local:42"


def test_url_eq() -> None:
    assert URL("") == URL("")
    assert URL("/foo") == "/foo"
    assert URL("") != 1


def test_url_repr() -> None:
    url = URL("https://foo:bar@testserver.local:42")
    assert repr(url) == "URL('https://foo:bar@testserver.local:42')"
