from typing import TYPE_CHECKING, Callable, Dict, List, TypeVar, Union

import pytest
from multidict import MultiDict

from starlite.datastructures.url import URL, make_absolute_url, parse_query_params

if TYPE_CHECKING:
    from starlite.types import Scope

T = TypeVar("T")


def multidict_to_list_dict(multidict: MultiDict[T]) -> Dict[str, List[T]]:
    result = {}
    for key in multidict:
        result[key] = multidict.getall(key)
    return result


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


@pytest.mark.parametrize(
    "query,expected",
    [
        ("param=value&param2=1&param=value2&empty=", {"param": ["value", "value2"], "param2": [True], "empty": [""]}),
        (
            "param=0&param2=false&param3=FaLse&param4=1&param5=true&param6=TRue",
            {
                "param": [False],
                "param2": [False],
                "param3": [False],
                "param4": [True],
                "param5": [True],
                "param6": [True],
            },
        ),
    ],
)
def test_parse_query_params(query: str, expected: Dict[str, List[Union[str, bool]]]) -> None:
    query_params = parse_query_params(query)
    assert multidict_to_list_dict(query_params) == expected


def test_url() -> None:
    url = URL("https://foo:hunter2@example.org:81/bar/baz?query=param&bool=1#fragment")
    assert url.scheme == "https"
    assert url.netloc == "foo:hunter2@example.org:81"
    assert url.path == "/bar/baz"
    assert url.query == "query=param&bool=1"
    assert url.fragment == "fragment"
    assert url.username == "foo"
    assert url.password == "hunter2"
    assert url.port == 81
    assert url.hostname == "example.org"
    assert url.query_params == MultiDict({"query": "param", "bool": True})


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
    "component,replacement",
    [
        ("scheme", "http"),
        ("netloc", "example.com"),
        ("path", "/foo"),
        ("query", "foo=baz"),
        ("fragment", "anchor2"),
    ],
)
def test_url_with_replacements(component: str, replacement: str) -> None:
    defaults = {
        "scheme": "https",
        "netloc": "example.org",
        "path": "/foo/bar",
        "query": "foo=bar",
        "fragment": "anchor",
    }
    url = URL.from_components(**defaults)
    defaults[component] = replacement
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
