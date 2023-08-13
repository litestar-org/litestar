import enum
from json import loads
from pathlib import Path, PurePath
from typing import Any, Dict, List

import msgspec
import pytest
from pydantic import SecretStr

from litestar import MediaType, Response
from litestar.contrib.pydantic import PydanticInitPlugin, _model_dump
from litestar.exceptions import ImproperlyConfiguredException
from litestar.serialization import get_serializer
from tests import (
    MsgSpecStructPerson,
    PydanticDataClassPerson,
    PydanticPerson,
    PydanticPersonFactory,
    VanillaDataClassPerson,
)

person = PydanticPersonFactory.build()
secret = SecretStr("secret_text")
pure_path = PurePath("/path/to/file")
path = Path("/path/to/file")


class _TestEnum(enum.Enum):
    A = "alpha"
    B = "beta"


@pytest.mark.parametrize("media_type", [MediaType.JSON, MediaType.MESSAGEPACK])
@pytest.mark.parametrize(
    "content, response_type",
    [
        [person, PydanticPerson],
        [{"key": 123}, Dict[str, int]],
        [[{"key": 123}], List[Dict[str, int]]],
        [VanillaDataClassPerson(**_model_dump(person)), VanillaDataClassPerson],
        [PydanticDataClassPerson(**_model_dump(person)), PydanticDataClassPerson],
        [MsgSpecStructPerson(**_model_dump(person)), MsgSpecStructPerson],
        [{"enum": _TestEnum.A}, Dict[str, _TestEnum]],
        [{"secret": secret}, Dict[str, SecretStr]],
        [{"pure_path": pure_path}, Dict[str, PurePath]],
        [{"path": path}, Dict[str, PurePath]],
    ],
)
def test_response_serialization_structured_types(content: Any, response_type: Any, media_type: MediaType) -> None:
    encoded = Response(None).render(
        content, media_type=media_type, enc_hook=get_serializer(type_encoders=PydanticInitPlugin.encoders())
    )
    if media_type == media_type.JSON:
        value = loads(encoded)
    else:
        value = msgspec.msgpack.decode(encoded)
    if isinstance(value, dict) and "enum" in value:
        assert content.__class__(**value)["enum"] == content["enum"].value
    elif isinstance(value, dict) and "secret" in value:
        assert content.__class__(**value)["secret"] == str(content["secret"])
    elif isinstance(value, dict) and "pure_path" in value:
        assert content.__class__(**value)["pure_path"] == str(content["pure_path"])
    elif isinstance(value, dict) and "path" in value:
        assert content.__class__(**value)["path"] == str(content["path"])
    elif isinstance(value, dict):
        assert content.__class__(**value) == content
    else:
        assert [content[0].__class__(**value[0])] == content


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
