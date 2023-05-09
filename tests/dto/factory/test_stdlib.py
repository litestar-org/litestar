from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import ClassVar, List

import pytest

from litestar.dto.factory.stdlib.dataclass import DataclassDTO
from litestar.dto.factory.types import FieldDefinition
from litestar.types.empty import Empty
from litestar.utils.helpers import get_fully_qualified_class_name
from litestar.utils.signature import ParsedType


@dataclass
class Model:
    a: int
    b: str = field(default="b")
    c: List[int] = field(default_factory=list)  # noqa: UP006
    d: ClassVar[float] = 1.0


@pytest.fixture(name="dto_type")
def fx_dto_type() -> type[DataclassDTO[Model]]:
    return DataclassDTO[Model]


@pytest.mark.skipif(sys.version_info > (3, 8), reason="generic builtin collection")
def test_dataclass_field_definitions(dto_type: type[DataclassDTO[Model]]) -> None:
    fqdn = get_fully_qualified_class_name(Model)
    assert list(dto_type.generate_field_definitions(Model)) == [
        FieldDefinition(
            name="a",
            parsed_type=ParsedType(int),
            default=Empty,
            default_factory=None,
            dto_field=None,
            unique_model_name=fqdn,
        ),
        FieldDefinition(
            name="b",
            parsed_type=ParsedType(str),
            default="b",
            default_factory=None,
            dto_field=None,
            unique_model_name=fqdn,
        ),
        FieldDefinition(
            name="c",
            parsed_type=ParsedType(list[int]),
            default=Empty,
            default_factory=list,
            dto_field=None,
            unique_model_name=fqdn,
        ),
    ]


def test_dataclass_field_definitions_38(dto_type: type[DataclassDTO[Model]]) -> None:
    fqdn = get_fully_qualified_class_name(Model)
    assert list(dto_type.generate_field_definitions(Model)) == [
        FieldDefinition(
            name="a",
            parsed_type=ParsedType(int),
            default=Empty,
            default_factory=None,
            dto_field=None,
            unique_model_name=fqdn,
        ),
        FieldDefinition(
            name="b",
            parsed_type=ParsedType(str),
            default="b",
            default_factory=None,
            dto_field=None,
            unique_model_name=fqdn,
        ),
        FieldDefinition(
            name="c",
            parsed_type=ParsedType(List[int]),
            default=Empty,
            default_factory=list,
            unique_model_name=fqdn,
            dto_field=None,
        ),
    ]


def test_dataclass_detect_nested(dto_type: type[DataclassDTO[Model]]) -> None:
    assert dto_type.detect_nested_field(ParsedType(Model)) is True
    assert dto_type.detect_nested_field(ParsedType(int)) is False
