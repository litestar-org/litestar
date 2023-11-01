import enum
from pathlib import Path, PurePath, PureWindowsPath
from typing import Any, Callable, cast

import msgspec
import pytest
from pytest import FixtureRequest

from litestar import MediaType, Response
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
