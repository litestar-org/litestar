import pytest

from starlite.utils.url import join_paths, normalize_path


@pytest.mark.parametrize(
    "base,fragment, expected",
    [
        ("/path/", "sub", "/path/sub"),
        ("path/", "sub", "/path/sub"),
        ("path", "sub", "/path/sub"),
        ("/path/", "sub/", "/path/sub"),
        ("path/", "sub/", "/path/sub"),
        ("path", "sub/", "/path/sub"),
    ],
)
def test_join_url_fragments(base: str, fragment: str, expected: str) -> None:
    assert join_paths([base, fragment]) == expected


@pytest.mark.parametrize(
    "base,expected",
    [
        ("", ""),
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
