from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import ClassVar, List

import pytest

from starlite.dto.stdlib.dataclass import DataclassDTO
from starlite.dto.types import FieldDefinition


@dataclass
class Model:
    a: int
    b: str = field(default="b")
    c: List[int] = field(default_factory=list)  # noqa: UP006
    d: ClassVar[float] = 1.0


@pytest.fixture(name="dto_type")
def fx_dto_type() -> type[DataclassDTO[Model]]:
    dto_type = DataclassDTO[Model]
    dto_type.postponed_cls_init()
    return dto_type


@pytest.mark.skipif(sys.version_info > (3, 8), reason="generic builtin collection")
def test_dataclass_field_definitions(dto_type: type[DataclassDTO[Model]]) -> None:
    assert list(dto_type.generate_field_definitions(Model)) == [
        FieldDefinition(field_name="a", field_type=int),
        FieldDefinition(field_name="b", field_type=str, default="b"),
        FieldDefinition(field_name="c", field_type=list[int], default_factory=list),
    ]


@pytest.mark.skipif(sys.version_info < (3, 9), reason="generic builtin collection")
def test_dataclass_field_definitions_38(dto_type: type[DataclassDTO[Model]]) -> None:
    assert list(dto_type.generate_field_definitions(Model)) == [
        FieldDefinition(field_name="a", field_type=int),
        FieldDefinition(field_name="b", field_type=str, default="b"),
        FieldDefinition(field_name="c", field_type=List[int], default_factory=list),
    ]


def test_dataclass_detect_nested(dto_type: type[DataclassDTO[Model]]) -> None:
    assert dto_type.detect_nested_field(FieldDefinition(field_name="a", field_type=Model)) is True
    assert dto_type.detect_nested_field(FieldDefinition(field_name="a", field_type=List[Model])) is True
    assert dto_type.detect_nested_field(FieldDefinition(field_name="a", field_type=int)) is False
