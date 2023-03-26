from __future__ import annotations

import sys
from typing import TYPE_CHECKING, List

import pytest
from msgspec import Struct, to_builtins

from starlite.dto.backends.msgspec import MsgspecDTOBackend
from starlite.dto.types import FieldDefinition, NestedFieldDefinition
from starlite.enums import MediaType
from starlite.exceptions import SerializationException

from . import Model

if TYPE_CHECKING:
    from starlite.dto.types import FieldDefinitionsType


class MyStruct(Struct):
    a: int
    b: str


@pytest.fixture(name="msgspec_backend")
def fx_msgspec_backend() -> MsgspecDTOBackend:
    return MsgspecDTOBackend(annotation=List[Model], data_container_type=MyStruct)


def test_dto_backend() -> None:
    field_definitions: FieldDefinitionsType = {
        "a": FieldDefinition(field_name="a", field_type=int),
        "b": FieldDefinition(field_name="b", field_type=str, default="b"),
        "c": FieldDefinition(field_name="c", field_type=List[int], default_factory=list),
        "nested": NestedFieldDefinition(
            field_definition=FieldDefinition(field_name="nested", field_type=Model),
            origin=None,
            args=(),
            nested_type=Model,
            nested_field_definitions={
                "a": FieldDefinition(field_name="a", field_type=int),
                "b": FieldDefinition(field_name="b", field_type=str),
            },
        ),
    }
    backend = MsgspecDTOBackend.from_field_definitions(type, field_definitions)
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


def test_msgspec_backend_scalar_annotation() -> None:
    msgspec_backend = MsgspecDTOBackend(annotation=Model, data_container_type=MyStruct)
    assert msgspec_backend.annotation == MyStruct
