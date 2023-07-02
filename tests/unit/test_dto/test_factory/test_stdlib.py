from __future__ import annotations

import sys
from dataclasses import dataclass, field
from typing import ClassVar, List

import pytest

from litestar.dto.factory import DTOField
from litestar.dto.factory.data_structures import FieldDefinition
from litestar.dto.factory.stdlib.dataclass import DataclassDTO
from litestar.typing import ParsedType
from litestar.utils.helpers import get_fully_qualified_class_name


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
        FieldDefinition.from_parsed_type(
            parsed_type=ParsedType.from_kwarg(
                name="a",
                annotation=int,
            ),
            default_factory=None,
            unique_model_name=fqdn,
            dto_field=DTOField(),
            dto_for=None,
        ),
        FieldDefinition.from_parsed_type(
            parsed_type=ParsedType.from_kwarg(
                name="b",
                annotation=str,
            ),
            default_factory=None,
            unique_model_name=fqdn,
            dto_field=DTOField(),
            dto_for=None,
        ),
        FieldDefinition.from_parsed_type(
            parsed_type=ParsedType.from_kwarg(
                name="c",
                annotation=list[int],
            ),
            default_factory=list,
            unique_model_name=fqdn,
            dto_field=DTOField(),
            dto_for=None,
        ),
    ]


def test_dataclass_field_definitions_38(dto_type: type[DataclassDTO[Model]]) -> None:
    fqdn = get_fully_qualified_class_name(Model)
    assert list(dto_type.generate_field_definitions(Model)) == [
        FieldDefinition.from_parsed_type(
            parsed_type=ParsedType.from_kwarg(
                name="a",
                annotation=int,
            ),
            default_factory=None,
            unique_model_name=fqdn,
            dto_field=DTOField(),
            dto_for=None,
        ),
        FieldDefinition.from_parsed_type(
            parsed_type=ParsedType.from_kwarg(
                name="b",
                annotation=str,
            ),
            default_factory=None,
            unique_model_name=fqdn,
            dto_field=DTOField(),
            dto_for=None,
        ),
        FieldDefinition.from_parsed_type(
            parsed_type=ParsedType.from_kwarg(
                name="c",
                annotation=List[int],
            ),
            default_factory=list,
            unique_model_name=fqdn,
            dto_field=DTOField(),
            dto_for=None,
        ),
    ]


def test_dataclass_detect_nested(dto_type: type[DataclassDTO[Model]]) -> None:
    assert dto_type.detect_nested_field(ParsedType.from_annotation(Model)) is True
    assert dto_type.detect_nested_field(ParsedType.from_annotation(int)) is False
