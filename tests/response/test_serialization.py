import enum
from json import loads
from pathlib import Path, PurePath
from typing import Any, Dict, List

import msgspec
import pytest
from pydantic import SecretStr

from litestar import MediaType, Response
from litestar.exceptions import ImproperlyConfiguredException
from litestar.status_codes import HTTP_200_OK
from tests import (
    MsgSpecStructPerson,
    Person,
    PersonFactory,
    PydanticDataClassPerson,
    VanillaDataClassPerson,
)

person = PersonFactory.build()
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
        [person, Person],
        [{"key": 123}, Dict[str, int]],
        [[{"key": 123}], List[Dict[str, int]]],
        [VanillaDataClassPerson(**person.dict()), VanillaDataClassPerson],
        [PydanticDataClassPerson(**person.dict()), PydanticDataClassPerson],
        [MsgSpecStructPerson(**person.dict()), MsgSpecStructPerson],
        [{"enum": _TestEnum.A}, Dict[str, _TestEnum]],
        [{"secret": secret}, Dict[str, SecretStr]],
        [{"pure_path": pure_path}, Dict[str, PurePath]],
        [{"path": path}, Dict[str, PurePath]],
    ],
)
def test_response_serialization_structured_types(content: Any, response_type: Any, media_type: MediaType) -> None:
    response = Response[response_type](content, media_type=media_type, status_code=HTTP_200_OK).to_asgi_response()
    if media_type == media_type.JSON:
        value = loads(response.body)
    else:
        value = msgspec.msgpack.decode(response.body)
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
    response = Response[response_type](content, media_type=media_type, status_code=HTTP_200_OK).to_asgi_response()
    assert response.body == content.encode("utf-8")


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
    if should_raise:
        with pytest.raises(ImproperlyConfiguredException):
            Response[response_type](content, media_type=media_type, status_code=HTTP_200_OK).to_asgi_response()
    else:
        response = Response[response_type](content, media_type=media_type, status_code=HTTP_200_OK).to_asgi_response()
        assert response.body == (content.encode("utf-8") if not isinstance(content, bytes) else content)
