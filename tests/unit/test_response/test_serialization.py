import enum
import re
from collections import deque
from collections.abc import Callable
from datetime import date, datetime, time
from decimal import Decimal
from ipaddress import IPv4Address, IPv4Network, IPv6Address, IPv6Network
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from typing import Any, cast

import msgspec
import pytest
from pytest import FixtureRequest

from litestar import MediaType, Response
from litestar.datastructures.secret_values import SecretBytes, SecretString
from litestar.exceptions import ImproperlyConfiguredException
from litestar.serialization import default_serializer, get_serializer
from litestar.serialization.msgspec_hooks import DEFAULT_TYPE_ENCODERS
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
    expected = r"\path\to\file" if isinstance(path, PureWindowsPath) else "/path/to/file"
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


@pytest.mark.parametrize(
    "value, expected",
    [
        (Path("/tmp/file"), "/tmp/file"),
        (PurePosixPath("/a/b"), "/a/b"),
        (IPv4Address("1.2.3.4"), "1.2.3.4"),
        (IPv4Network("192.0.2.0/24"), "192.0.2.0/24"),
        (IPv6Address("::1"), "::1"),
        (IPv6Network("::1/128"), "::1/128"),
        (datetime(2024, 1, 15, 12, 0, 0), "2024-01-15T12:00:00"),
        (date(2024, 1, 15), "2024-01-15"),
        (time(12, 30, 0), "12:30:00"),
        (deque([1, 2, 3]), [1, 2, 3]),
        (Decimal("3.14"), 3.14),
        (Decimal("42"), 42),
        (re.compile(r"\d+"), r"\d+"),
        (SecretString("s3cr3t"), "******"),
        (SecretBytes(b"s3cr3t"), "******"),
    ],
)
def test_default_serializer_builtin_types(value: Any, expected: Any) -> None:
    assert default_serializer(value) == expected


def test_default_serializer_unsupported_type_raises() -> None:
    class Unregistered:
        pass

    with pytest.raises(TypeError, match="Unsupported type"):
        default_serializer(Unregistered())


def test_default_serializer_empty_type_encoders_preserves_defaults() -> None:
    """Falsy type_encoders={} must not suppress DEFAULT_TYPE_ENCODERS."""
    assert default_serializer(Path("/tmp"), type_encoders={}) == default_serializer(Path("/tmp"), type_encoders=None)


def test_default_serializer_custom_encoder_overrides_default() -> None:
    assert default_serializer(Path("/x"), type_encoders={Path: lambda v: "overridden"}) == "overridden"


def test_default_serializer_custom_encoder_extends_defaults() -> None:
    class Custom:
        pass

    result_custom = default_serializer(Custom(), type_encoders={Custom: lambda v: "custom"})
    result_default = default_serializer(Path("/x"), type_encoders={Custom: lambda v: "custom"})
    assert result_custom == "custom"
    assert result_default == "/x"


def test_default_serializer_mro_subclass_uses_base_encoder() -> None:
    class Base:
        pass

    class Child(Base):
        pass

    assert default_serializer(Child(), type_encoders={Base: lambda v: "base"}) == "base"


def test_default_serializer_mro_subclass_encoder_takes_priority() -> None:
    class Base:
        pass

    class Child(Base):
        pass

    result = default_serializer(Child(), type_encoders={Base: lambda v: "base", Child: lambda v: "child"})
    assert result == "child"


def test_default_serializer_repeated_calls_consistent() -> None:
    """Same type serialized multiple times must always return the same result."""
    values = [Decimal("1.5"), Decimal("2.5"), Decimal("3.0")]
    assert [default_serializer(v) for v in values] == [1.5, 2.5, 3.0]


def test_default_serializer_does_not_mutate_default_type_encoders() -> None:
    snapshot = dict(DEFAULT_TYPE_ENCODERS)

    class Extra:
        pass

    default_serializer(Path("/x"), type_encoders={Extra: lambda v: "extra"})
    assert dict(DEFAULT_TYPE_ENCODERS) == snapshot


def test_get_serializer_custom_encoders_independent() -> None:
    """Two serializers from get_serializer must not share per-type state."""

    class Foo:
        pass

    s1 = get_serializer({Foo: lambda v: "s1"})
    s2 = get_serializer({Foo: lambda v: "s2"})
    assert s1(Foo()) == "s1"
    assert s2(Foo()) == "s2"
    assert s1(Foo()) == "s1"
