import pytest

from litestar.utils.path import join_paths, normalize_path


@pytest.mark.parametrize(
    "base,fragment, expected",
    (
        ("/path/", "sub", "/path/sub"),
        ("/path/", "/sub/", "/path/sub"),
        ("path/", "sub", "/path/sub"),
        ("path", "sub", "/path/sub"),
        ("/path/", "sub/", "/path/sub"),
        ("path/", "sub/", "/path/sub"),
        ("path", "sub/", "/path/sub"),
        ("/", "/root/sub", "/root/sub"),
    ),
)
def test_join_url_fragments(base: str, fragment: str, expected: str) -> None:
    assert join_paths([base, fragment]) == expected


def test_join_empty_list() -> None:
    assert join_paths([]) == "/"


def test_join_single() -> None:
    assert join_paths([""]) == "/"
    assert join_paths(["/"]) == "/"
    assert join_paths(["root"]) == "/root"
    assert join_paths(["root//other"]) == "/root/other"


@pytest.mark.parametrize(
    "base,expected",
    [
        ("", "/"),
        ("/path", "/path"),
        ("path/", "/path"),
        ("path", "/path"),
        ("path////path", "/path/path"),
        ("path//", "/path"),
        ("///", "/"),
    ],
)
def test_normalize_path(base: str, expected: str) -> None:
    assert normalize_path(base) == expected
