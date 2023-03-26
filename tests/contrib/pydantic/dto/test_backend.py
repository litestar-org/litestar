from __future__ import annotations

import sys
from typing import TYPE_CHECKING, List

import pytest
from pydantic import BaseModel

from starlite.contrib.pydantic.dto.backend import PydanticDTOBackend
from starlite.dto.types import FieldDefinition, NestedFieldDefinition
from starlite.enums import MediaType
from starlite.exceptions import SerializationException
from tests.dto import Model

if TYPE_CHECKING:
    from starlite.dto.types import FieldDefinitionsType


class MyModel(BaseModel):
    a: int
    b: str


@pytest.fixture(name="pydantic_backend")
def fx_pydantic_backend() -> PydanticDTOBackend:
    return PydanticDTOBackend(annotation=List[Model], data_container_type=MyModel)


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
    backend = PydanticDTOBackend.from_field_definitions(type, field_definitions)
    assert backend.parse_raw(b'{"a":1,"nested":{"a":1,"b":"two"}}', media_type=MediaType.JSON) == {
        "a": 1,
        "b": "b",
        "c": [],
        "nested": {"a": 1, "b": "two"},
    }


def test_pydantic_backend_parse_unsupported_media_type(pydantic_backend: PydanticDTOBackend) -> None:
    with pytest.raises(SerializationException):
        pydantic_backend.parse_raw(b"", media_type=MediaType.MESSAGEPACK)


def test_pydantic_backend_iterable_annotation(pydantic_backend: PydanticDTOBackend) -> None:
    if sys.version_info < (3, 9):
        assert pydantic_backend.annotation == List[MyModel]
    else:
        assert pydantic_backend.annotation == list[MyModel]


def test_pydantic_backend_scalar_annotation() -> None:
    pydantic_backend = PydanticDTOBackend(annotation=Model, data_container_type=MyModel)
    assert pydantic_backend.annotation == MyModel
