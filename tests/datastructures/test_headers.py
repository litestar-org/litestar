"""Parts of the code testing `MutableHeaders` and parts of `Headers` was
adopted from https://github.com/encode/starlette/blob/e7d000a76d9e4ea5951a8b3b0
28a057e4df9484c/tests/test_datastructures.py.

Copyright © 2018, [Encode OSS Ltd](https://www.encode.io/).
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice,
  this list of conditions and the following disclaimer in the documentation
  and/or other materials provided with the distribution.

* Neither the name of the copyright holder nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import pytest
from pydantic import ValidationError

from starlite.datastructures import CacheControlHeader, ETag, Headers, MutableHeaders
from starlite.exceptions import ImproperlyConfiguredException


def test_headers() -> None:
    h = Headers([(b"a", b"123"), (b"a", b"456"), (b"b", b"789")])
    assert "a" in h
    assert "A" in h
    assert "b" in h
    assert "B" in h
    assert "c" not in h
    assert h["a"] == "123"
    assert h.get("a") == "123"
    assert h.get("nope", default=None) is None
    assert h.getlist("a") == ["123", "456"]
    assert h.keys() == ["a", "a", "b"]
    assert h.values() == ["123", "456", "789"]
    assert h.items() == [("a", "123"), ("a", "456"), ("b", "789")]
    assert list(h) == ["a", "a", "b"]
    assert dict(h) == {"a": "123", "b": "789"}
    assert h != Headers([(b"a", b"123"), (b"b", b"789"), (b"a", b"456")])
    assert h != [(b"a", b"123"), (b"A", b"456"), (b"b", b"789")]  # type: ignore[comparison-overlap]

    h = Headers({"a": "123", "b": "789"})
    assert h["A"] == "123"
    assert h["B"] == "789"
    assert sorted(h.raw) == sorted([(b"a", b"123"), (b"b", b"789")])


def test_mutable_headers() -> None:
    h = MutableHeaders()
    assert dict(h) == {}
    h["a"] = "1"
    assert dict(h) == {"a": "1"}
    h["a"] = "2"
    assert dict(h) == {"a": "2"}
    h.setdefault("a", "3")
    assert dict(h) == {"a": "2"}
    h.setdefault("b", "4")
    assert dict(h) == {"a": "2", "b": "4"}
    del h["a"]
    assert dict(h) == {"b": "4"}
    assert h.raw == [(b"b", b"4")]


def test_mutable_headers_merge() -> None:
    h = MutableHeaders()
    h = h | MutableHeaders({"a": "1"})
    assert isinstance(h, MutableHeaders)
    assert dict(h) == {"a": "1"}
    assert h.items() == [("a", "1")]
    assert h.raw == [(b"a", b"1")]


def test_mutable_headers_merge_dict() -> None:
    h = MutableHeaders()
    h = h | {"a": "1"}
    assert isinstance(h, MutableHeaders)
    assert dict(h) == {"a": "1"}
    assert h.items() == [("a", "1")]
    assert h.raw == [(b"a", b"1")]


def test_mutable_headers_update() -> None:
    h = MutableHeaders()
    h |= MutableHeaders({"a": "1"})
    assert isinstance(h, MutableHeaders)
    assert dict(h) == {"a": "1"}
    assert h.items() == [("a", "1")]
    assert h.raw == [(b"a", b"1")]


def test_mutable_headers_update_dict() -> None:
    h = MutableHeaders()
    h |= {"a": "1"}
    assert isinstance(h, MutableHeaders)
    assert dict(h) == {"a": "1"}
    assert h.items() == [("a", "1")]
    assert h.raw == [(b"a", b"1")]


def test_mutable_headers_merge_not_mapping() -> None:
    h = MutableHeaders()
    with pytest.raises(TypeError):
        h |= {"not_mapping"}  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        h | {"not_mapping"}  # type: ignore[operator]


def test_headers_mutablecopy() -> None:
    h = Headers([(b"a", b"123"), (b"a", b"456"), (b"b", b"789")])
    copy = h.mutablecopy()
    assert sorted(copy.items()) == sorted([("a", "123"), ("a", "456"), ("b", "789")])
    copy["a"] = "abc"
    assert sorted(copy.items()) == sorted([("a", "abc"), ("b", "789")])


def test_mutable_headers_from_scope() -> None:
    h = MutableHeaders.from_scope({"headers": [(b"a", b"1")]})  # type: ignore
    assert dict(h) == {"a": "1"}
    h.update({"b": "2"})
    assert dict(h) == {"a": "1", "b": "2"}
    assert list(h.items()) == [("a", "1"), ("b", "2")]
    assert list(h.raw) == [(b"a", b"1"), (b"b", b"2")]


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


@pytest.mark.parametrize("invalid_value", ["x=y=z", "x, ", "no-cache=10"])
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


@pytest.mark.parametrize("value", ['W/"foo"', 'w/"foo"'])
def test_etag_from_header_weak(value: str) -> None:
    etag = ETag.from_header(value)
    assert etag.value == "foo"
    assert etag.weak is True


@pytest.mark.parametrize("value", ['"føo"', 'W/"føo"'])
def test_etag_from_header_non_ascii_value(value: str) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ETag.from_header(value)


@pytest.mark.parametrize("value", ["foo", "W/foo"])
def test_etag_from_header_missing_quotes(value: str) -> None:
    with pytest.raises(ImproperlyConfiguredException):
        ETag.from_header(value)


def test_etag_to_header() -> None:
    assert ETag(value="foo").to_header() == '"foo"'


def test_etag_to_header_weak() -> None:
    assert ETag(value="foo", weak=True).to_header() == 'W/"foo"'
