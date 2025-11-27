import enum
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any, Callable, cast

import msgspec
import pytest
from pytest import FixtureRequest

from litestar import MediaType, Response, get
from litestar.exceptions import ImproperlyConfiguredException
from litestar.serialization import get_serializer
from tests.models import DataclassPersonFactory, MsgSpecStructPerson

person = DataclassPersonFactory.build()


class _TestEnum(enum.Enum):
    A = "alpha"
    B = "beta"


@pytest.fixture(params=[MediaType.JSON, MediaType.MESSAGEPACK])
def media_type(request: FixtureRequest) -> MediaType:
    return cast(MediaType, request.param)


DecodeMediaType = Callable[[Any], Any]


@pytest.fixture()
def decode_media_type(media_type: MediaType) -> DecodeMediaType:
    if media_type == MediaType.JSON:
        return msgspec.json.decode
    return msgspec.msgpack.decode


def test_dataclass(media_type: MediaType, decode_media_type: DecodeMediaType) -> None:
    encoded = Response(None).render(person, media_type=media_type)
    assert decode_media_type(encoded) == msgspec.to_builtins(person)


def test_struct(media_type: MediaType, decode_media_type: DecodeMediaType) -> None:
    encoded = Response(None).render(MsgSpecStructPerson(**msgspec.to_builtins(person)), media_type=media_type)
    assert decode_media_type(encoded) == msgspec.to_builtins(person)


@pytest.mark.parametrize("content", [{"value": 1}, [{"value": 1}]])
def test_dict(media_type: MediaType, decode_media_type: DecodeMediaType, content: Any) -> None:
    encoded = Response(None).render(content, media_type=media_type)
    assert decode_media_type(encoded) == content


def test_enum(media_type: MediaType, decode_media_type: DecodeMediaType) -> None:
    encoded = Response(None).render({"value": _TestEnum.A}, media_type=media_type)
    assert decode_media_type(encoded) == {"value": _TestEnum.A.value}


@pytest.mark.parametrize("path", [PurePath("/path/to/file"), Path("/path/to/file")])
def test_path(media_type: MediaType, decode_media_type: DecodeMediaType, path: Path) -> None:
    encoded = Response(None).render({"value": path}, media_type=media_type)
    expected = r"\\path\\to\\file" if isinstance(path, PureWindowsPath) else "/path/to/file"
    assert decode_media_type(encoded) == {"value": expected}


@pytest.mark.parametrize(
    "content, response_type, media_type", [["abcdefg", str, MediaType.TEXT], ["<div/>", str, MediaType.HTML]]
)
def test_response_serialization_text_types(content: Any, response_type: Any, media_type: MediaType) -> None:
    assert Response(None).render(content, media_type=media_type, enc_hook=get_serializer({})) == content.encode("utf-8")


@pytest.mark.parametrize(
    "content, response_type, media_type, should_raise",
    [
        ["abcdefg", str, "text/custom", False],
        ["<xml/>", str, "application/unknown", False],
        [b"<xml/>", bytes, "application/unknown", False],
        [{"key": "value"}, dict, "application/unknown", True],
    ],
)
def test_response_validation_of_unknown_media_types(
    content: Any, response_type: Any, media_type: MediaType, should_raise: bool
) -> None:
    response = Response(None)
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            response.render(content, media_type=media_type)
    else:
        rendered = response.render(content, media_type=media_type)
        assert rendered == (content if isinstance(content, bytes) else content.encode("utf-8"))


def test_string_serialization_with_json_media_type() -> None:
    content = "foo"
    encoded = Response(None).render(content, media_type=MediaType.JSON)
    assert encoded == b'"foo"'
    assert msgspec.json.decode(encoded) == "foo"


def test_string_serialization_with_msgpack_media_type() -> None:
    content = "foo"
    encoded = Response(None).render(content, media_type=MediaType.MESSAGEPACK)
    assert msgspec.msgpack.decode(encoded) == "foo"


def test_msgspec_raw_serialization_with_json() -> None:
    """Test that msgspec.Raw content is returned as-is with JSON media type."""
    content = msgspec.Raw(b'{"foo": "bar"}')
    encoded = Response(None).render(content, media_type=MediaType.JSON)
    assert encoded == b'{"foo": "bar"}'
    # Verify it's valid JSON
    assert msgspec.json.decode(encoded) == {"foo": "bar"}


def test_msgspec_raw_serialization_with_msgpack() -> None:
    """Test that msgspec.Raw content is returned as-is with msgpack media type."""
    # Pre-encode some data with msgpack
    original_data = {"key": "value", "number": 42}
    pre_encoded = msgspec.msgpack.encode(original_data)
    content = msgspec.Raw(pre_encoded)

    encoded = Response(None).render(content, media_type=MediaType.MESSAGEPACK)
    assert encoded == pre_encoded
    # Verify it decodes correctly
    assert msgspec.msgpack.decode(encoded) == original_data


def test_msgspec_raw_serialization_with_text() -> None:
    """Test that msgspec.Raw content is returned as-is with text media type."""
    content = msgspec.Raw(b'plain text content')
    encoded = Response(None).render(content, media_type=MediaType.TEXT)
    assert encoded == b'plain text content'


def test_msgspec_raw_with_pre_encoded_html() -> None:
    """Test that msgspec.Raw works with pre-encoded HTML content."""
    html_content = b'<div>Hello <strong>World</strong></div>'
    content = msgspec.Raw(html_content)
    encoded = Response(None).render(content, media_type=MediaType.HTML)
    assert encoded == html_content


def test_bytes_content_with_json_media_type() -> None:
    """Test that bytes content is returned as-is regardless of media type."""
    content = b'{"already": "encoded"}'
    encoded = Response(None).render(content, media_type=MediaType.JSON)
    assert encoded == content


def test_bytes_content_with_text_media_type() -> None:
    """Test that bytes content is returned as-is with text media type."""
    content = b'plain bytes'
    encoded = Response(None).render(content, media_type=MediaType.TEXT)
    assert encoded == content


def test_empty_string_with_json_media_type() -> None:
    """Test that empty string with JSON media type produces valid JSON."""
    content = ""
    encoded = Response(None).render(content, media_type=MediaType.JSON)
    assert encoded == b'""'
    assert msgspec.json.decode(encoded) == ""


def test_empty_string_with_text_media_type() -> None:
    """Test that empty string with text media type produces empty bytes."""
    content = ""
    encoded = Response(None).render(content, media_type=MediaType.TEXT)
    assert encoded == b""


def test_json_like_string_gets_properly_quoted() -> None:
    """Test that JSON-like strings are properly quoted when media type is JSON."""
    content = '{"this": "looks like json"}'
    encoded = Response(None).render(content, media_type=MediaType.JSON)
    # Should be double-encoded: the string itself becomes a JSON string
    assert encoded == b'"{\\\"this\\\": \\\"looks like json\\\"}"'
    # When decoded, we get back the original string
    assert msgspec.json.decode(encoded) == content


def test_literal_string_values_with_json() -> None:
    """Test that literal string values work correctly with JSON media type."""
    # This addresses the core issue #4473
    content = "enabled"  # Could be from Literal["enabled", "disabled"]
    encoded = Response(None).render(content, media_type=MediaType.JSON)
    assert encoded == b'"enabled"'
    assert msgspec.json.decode(encoded) == "enabled"


def test_string_with_special_characters_json() -> None:
    """Test that strings with special characters are properly escaped in JSON."""
    content = 'Hello "World"\nNew Line\tTab'
    encoded = Response(None).render(content, media_type=MediaType.JSON)
    # Should be properly JSON-encoded
    decoded = msgspec.json.decode(encoded)
    assert decoded == content


def test_application_json_variants() -> None:
    """Test that various application/json variants are handled correctly."""
    content = "test"

    # Standard application/json
    encoded = Response(None).render(content, media_type="application/json")
    assert encoded == b'"test"'

    # application/vnd.api+json (JSON API spec)
    encoded = Response(None).render(content, media_type="application/vnd.api+json")
    assert encoded == b'"test"'

    # application/ld+json (JSON-LD)
    encoded = Response(None).render(content, media_type="application/ld+json")
    assert encoded == b'"test"'


# Tests for type-based media_type inference (issue #4473)


def test_media_type_inference_str_defaults_to_text() -> None:
    """Test that str content without explicit media_type defaults to text/plain."""
    from litestar.testing import create_test_client

    @get("/test")
    def handler() -> str:
        return "hello world"

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/test")
        assert response.status_code == 200
        assert response.text == "hello world"
        assert response.headers["content-type"].startswith("text/plain")


def test_media_type_inference_str_with_explicit_json() -> None:
    """Test that str content with explicit JSON media_type is JSON-encoded."""
    from litestar.testing import create_test_client

    @get("/test", media_type=MediaType.JSON)
    def handler() -> str:
        return "hello world"

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == "hello world"  # Should be properly quoted JSON
        assert response.headers["content-type"].startswith("application/json")


def test_media_type_inference_literal_defaults_to_text() -> None:
    """Test that Literal[str] content without explicit media_type defaults to text/plain.

    Note: Literal types are treated the same as their base type (str) at runtime,
    so they also default to text/plain when no explicit media_type is provided.
    """
    from litestar.testing import create_test_client
    from typing import Literal

    @get("/test")
    def handler() -> Literal["enabled", "disabled"]:
        return "enabled"

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/test")
        assert response.status_code == 200
        assert response.text == "enabled"
        # Check that it starts with text/plain (may include charset)
        content_type = response.headers.get("content-type", "")
        assert "text/plain" in content_type


def test_media_type_inference_literal_with_explicit_json() -> None:
    """Test that Literal content with explicit JSON media_type is JSON-encoded (issue #4473)."""
    from litestar.testing import create_test_client
    from typing import Literal

    @get("/test", media_type=MediaType.JSON)
    def handler() -> Literal["enabled", "disabled"]:
        return "enabled"

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == "enabled"  # Should be properly quoted JSON string
        assert response.headers["content-type"].startswith("application/json")


def test_media_type_inference_dict_defaults_to_json() -> None:
    """Test that dict content without explicit media_type defaults to application/json."""
    from litestar.testing import create_test_client

    @get("/test")
    def handler() -> dict[str, str]:
        return {"message": "hello"}

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == {"message": "hello"}
        assert response.headers["content-type"].startswith("application/json")


def test_media_type_inference_list_defaults_to_json() -> None:
    """Test that list content without explicit media_type defaults to application/json."""
    from litestar.testing import create_test_client

    @get("/test")
    def handler() -> list[str]:
        return ["a", "b", "c"]

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/test")
        assert response.status_code == 200
        assert response.json() == ["a", "b", "c"]
        assert response.headers["content-type"].startswith("application/json")


def test_media_type_inference_bytes_defaults_to_text() -> None:
    """Test that bytes content without explicit media_type defaults to text/plain."""
    from litestar.testing import create_test_client

    @get("/test")
    def handler() -> bytes:
        return b"binary data"

    with create_test_client(route_handlers=[handler]) as client:
        response = client.get("/test")
        assert response.status_code == 200
        assert response.content == b"binary data"
        assert response.headers["content-type"].startswith("text/plain")


def test_media_type_explicit_always_wins() -> None:
    """Test that explicit media_type always takes precedence over inferred type."""
    from litestar.testing import create_test_client

    # String with explicit JSON (would normally be text/plain)
    @get("/str-as-json", media_type=MediaType.JSON)
    def handler_str() -> str:
        return "forced to json"

    with create_test_client(route_handlers=[handler_str]) as client:
        response = client.get("/str-as-json")
        assert response.status_code == 200
        # String is JSON-encoded because of explicit media_type
        assert response.json() == "forced to json"
        assert response.headers["content-type"].startswith("application/json")

