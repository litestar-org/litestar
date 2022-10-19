import pytest

from starlite.datastructures import CacheControlHeader
from starlite.exceptions import ImproperlyConfiguredException


def test_cache_control_to_header() -> None:
    header = CacheControlHeader(max_age=10, private=True)
    expected_header_values = ["max-age=10, private", "private, max-age=10"]
    assert header.to_header() in expected_header_values
    assert header.to_header(include_header_name=True) in [f"cache-control: {v}" for v in expected_header_values]


def test_cache_control_from_header() -> None:
    header_value = "public, max-age=31536000"
    header = CacheControlHeader.from_header(header_value)
    header_dict = header.dict(exclude_unset=True, exclude_none=True, by_alias=True)
    assert header_dict == {"public": True, "max-age": 31536000}


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
