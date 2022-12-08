import enum
from json import loads
from pathlib import PurePath
from typing import Any, Dict, List

import msgspec
import pytest
from pydantic import SecretStr

from starlite import MediaType, Response
from starlite.status_codes import HTTP_200_OK
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
    ],
)
def test_response_serialization_structured_types(content: Any, response_type: Any, media_type: MediaType) -> None:
    response = Response[response_type](  # type: ignore[valid-type]
        content, media_type=media_type, status_code=HTTP_200_OK
    )
    if media_type == media_type.JSON:
        value = loads(response.body)
    else:
        value = msgspec.msgpack.decode(response.body)
    if isinstance(value, dict) and "enum" in value:
        assert content.__class__(**value)["enum"] == content["enum"].value
    elif isinstance(value, dict) and "secret" in value:
        assert content.__class__(**value)["secret"] == content["secret"].get_secret_value()
    elif isinstance(value, dict) and "pure_path" in value:
        assert content.__class__(**value)["pure_path"] == str(content["pure_path"])
    elif isinstance(value, dict):

        assert content.__class__(**value) == content
    else:
        assert [content[0].__class__(**value[0])] == content


@pytest.mark.parametrize(
    "content, response_type, media_type", [["abcdefg", str, MediaType.TEXT], ["<div/>", str, MediaType.HTML]]
)
def test_response_serialization_text_types(content: Any, response_type: Any, media_type: MediaType) -> None:
    response = Response[response_type](  # type: ignore[valid-type]
        content, media_type=media_type, status_code=HTTP_200_OK
    )
    assert response.body == content.encode("utf-8")
