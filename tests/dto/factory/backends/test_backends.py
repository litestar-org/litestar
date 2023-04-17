from __future__ import annotations

import sys
from typing import TYPE_CHECKING, List

import pytest
from msgspec import Struct, to_builtins

from litestar.dto.factory.backends import MsgspecDTOBackend
from litestar.dto.factory.types import FieldDefinition, NestedFieldDefinition
from litestar.enums import MediaType
from litestar.exceptions import SerializationException
from litestar.types.empty import Empty
from litestar.utils.signature import ParsedType
from tests.dto import Model

if TYPE_CHECKING:
    from litestar.dto.factory.types import FieldDefinitionsType


class MyStruct(Struct):
    a: int
    b: str


@pytest.fixture(name="field_definitions")
def fx_field_definitions() -> FieldDefinitionsType:
    return {
        "a": FieldDefinition(name="a", parsed_type=ParsedType(int), default=Empty),
        "b": FieldDefinition(name="b", parsed_type=ParsedType(str), default="b"),
        "c": FieldDefinition(name="c", parsed_type=ParsedType(List[int]), default_factory=list, default=Empty),
        "nested": NestedFieldDefinition(
            field_definition=FieldDefinition(name="nested", parsed_type=ParsedType(Model), default=Empty),
            nested_type=Model,
            nested_field_definitions={
                "a": FieldDefinition(name="a", parsed_type=ParsedType(int), default=Empty),
                "b": FieldDefinition(name="b", parsed_type=ParsedType(str), default=Empty),
            },
        ),
    }


@pytest.fixture(name="msgspec_backend")
def fx_msgspec_backend(field_definitions: FieldDefinitionsType) -> MsgspecDTOBackend:
    return MsgspecDTOBackend(
        parsed_type=ParsedType(List[Model]), data_container_type=MyStruct, field_definitions=field_definitions
    )


def test_dto_backend(field_definitions: FieldDefinitionsType) -> None:
    backend = MsgspecDTOBackend.from_field_definitions(ParsedType(type), field_definitions)
    assert to_builtins(backend.parse_raw(b'{"a":1,"nested":{"a":1,"b":"two"}}', media_type=MediaType.JSON)) == {
        "a": 1,
        "b": "b",
        "c": [],
        "nested": {"a": 1, "b": "two"},
    }


def test_msgspec_backend_parse_raw_msgpack(msgspec_backend: MsgspecDTOBackend) -> None:
    assert to_builtins(
        msgspec_backend.parse_raw(b"\x91\x82\xa1a\x01\xa1b\xa3two", media_type=MediaType.MESSAGEPACK)
    ) == [
        {
            "a": 1,
            "b": "two",
        }
    ]


def test_msgspec_backend_parse_unsupported_media_type(msgspec_backend: MsgspecDTOBackend) -> None:
    with pytest.raises(SerializationException):
        msgspec_backend.parse_raw(b"", media_type=MediaType.CSS)


def test_msgspec_backend_iterable_annotation(msgspec_backend: MsgspecDTOBackend) -> None:
    if sys.version_info < (3, 9):
        assert msgspec_backend.annotation == List[MyStruct]
    else:
        assert msgspec_backend.annotation == list[MyStruct]


def test_msgspec_backend_scalar_annotation(field_definitions: FieldDefinitionsType) -> None:
    msgspec_backend = MsgspecDTOBackend(
        parsed_type=ParsedType(Model), data_container_type=MyStruct, field_definitions=field_definitions
    )
    assert msgspec_backend.annotation == MyStruct
