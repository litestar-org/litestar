from __future__ import annotations

import sys
from typing import TYPE_CHECKING, List

import pytest
from msgspec import Struct, to_builtins
from pydantic import BaseModel

from starlite.dto.backends.msgspec import MsgspecDTOBackend
from starlite.dto.backends.pydantic import PydanticDTOBackend
from starlite.dto.types import FieldDefinition, NestedFieldDefinition
from starlite.enums import MediaType
from starlite.exceptions import SerializationException

from . import Model

if TYPE_CHECKING:
    from starlite.dto.backends.abc import AbstractDTOBackend
    from starlite.dto.types import FieldDefinitionsType


class MyStruct(Struct):
    a: int
    b: str


class MyModel(BaseModel):
    a: int
    b: str


@pytest.fixture(name="msgspec_backend")
def fx_msgspec_backend() -> MsgspecDTOBackend:
    return MsgspecDTOBackend(annotation=List[Model], model=MyStruct)


@pytest.fixture(name="pydantic_backend")
def fx_pydantic_backend() -> PydanticDTOBackend:
    return PydanticDTOBackend(annotation=List[Model], model=MyModel)


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_dto_backends(backend_type: type[AbstractDTOBackend]) -> None:
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
    backend = backend_type.from_field_definitions(type, field_definitions)
    if isinstance(backend, PydanticDTOBackend):
        assert backend.parse_raw(b'{"a":1,"nested":{"a":1,"b":"two"}}', media_type=MediaType.JSON) == {
            "a": 1,
            "b": "b",
            "c": [],
            "nested": {"a": 1, "b": "two"},
        }
    else:
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
    msgspec_backend = MsgspecDTOBackend(annotation=Model, model=MyStruct)
    assert msgspec_backend.annotation == MyStruct


def test_pydantic_backend_parse_unsupported_media_type(pydantic_backend: PydanticDTOBackend) -> None:
    with pytest.raises(SerializationException):
        pydantic_backend.parse_raw(b"", media_type=MediaType.MESSAGEPACK)


def test_pydantic_backend_iterable_annotation(pydantic_backend: PydanticDTOBackend) -> None:
    if sys.version_info < (3, 9):
        assert pydantic_backend.annotation == List[MyModel]
    else:
        assert pydantic_backend.annotation == list[MyModel]


def test_pydantic_backend_scalar_annotation() -> None:
    pydantic_backend = PydanticDTOBackend(annotation=Model, model=MyModel)
    assert pydantic_backend.annotation == MyModel
