import pytest
from pydantic import ValidationError

from starlite.datastructures import CacheControlHeader, ETag
from starlite.exceptions import ImproperlyConfiguredException


def test_cache_control_to_header() -> None:
    header = CacheControlHeader(max_age=10, private=True)
    expected_header_values = ["max-age=10, private", "private, max-age=10"]
    assert header.to_header() in expected_header_values
    assert header.to_header(include_header_name=True) in [f"cache-control: {v}" for v in expected_header_values]


def test_cache_control_from_header() -> None:
    header_value = (
        "public, private, no-store, no-cache, max-age=10000, s-maxage=1000, no-transform, "
        "must-revalidate, proxy-revalidate, must-understand, immutable, stale-while-revalidate=100"
    )
    header = CacheControlHeader.from_header(header_value)
    assert header.dict() == {
        "documentation_only": False,
        "public": True,
        "private": True,
        "no_store": True,
        "no_cache": True,
        "max_age": 10000,
        "s_maxage": 1000,
        "no_transform": True,
        "must_revalidate": True,
        "proxy_revalidate": True,
        "must_understand": True,
        "immutable": True,
        "stale_while_revalidate": 100,
    }


def test_cache_control_from_header_single_value() -> None:
    header_value = "no-cache"
    header = CacheControlHeader.from_header(header_value)
    header_dict = header.dict(exclude_unset=True, exclude_none=True, by_alias=True)
    assert header_dict == {"no-cache": True}


@pytest.mark.parametrize("invalid_value", ["x=y=z", "x, ", "no-cache=10"])  # type: ignore[misc]
def test_cache_control_from_header_invalid_value(invalid_value: str) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        CacheControlHeader.from_header(invalid_value)


def test_cache_control_header_prevent_storing() -> None:
    header = CacheControlHeader.prevent_storing()
    header_dict = header.dict(exclude_unset=True, exclude_none=True, by_alias=True)
    assert header_dict == {"no-store": True}


def test_etag_documentation_only() -> None:
    assert ETag(documentation_only=True).value is None


def test_etag_no_value() -> None:
    with pytest.raises(ValidationError):
        ETag()

    with pytest.raises(ValidationError):
        ETag(weak=True)


def test_etag_non_ascii() -> None:
    with pytest.raises(ValidationError):
        ETag(value="f↓o")


def test_etag_from_header() -> None:
    etag = ETag.from_header('"foo"')
    assert etag.value == "foo"
    assert etag.weak is False


@pytest.mark.parametrize("value", ['W/"foo"', 'w/"foo"'])  # type: ignore[misc]
def test_etag_from_header_weak(value: str) -> None:
    etag = ETag.from_header(value)
    assert etag.value == "foo"
    assert etag.weak is True


@pytest.mark.parametrize("value", ['"føo"', 'W/"føo"'])  # type: ignore[misc]
def test_etag_from_header_non_ascii_value(value: str) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ETag.from_header(value)


@pytest.mark.parametrize("value", ["foo", "W/foo"])  # type: ignore[misc]
def test_etag_from_header_missing_quotes(value: str) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ETag.from_header(value)


def test_etag_to_header() -> None:
    assert ETag(value="foo").to_header() == '"foo"'


def test_etag_to_header_weak() -> None:
    assert ETag(value="foo", weak=True).to_header() == 'W/"foo"'
