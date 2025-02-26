from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING, Annotated, Callable, Optional
from unittest.mock import ANY

import pydantic as pydantic_v2
import pytest
from pydantic import v1 as pydantic_v1

from litestar.dto import DTOField, DTOFieldDefinition, Mark, dto_field
from litestar.plugins.pydantic import PydanticDTO
from litestar.typing import FieldDefinition

from . import PydanticVersion

if TYPE_CHECKING:
    from typing import Callable


@pytest.fixture
def expected_field_defs(int_factory: Callable[[], int]) -> list[DTOFieldDefinition]:
    return [
        DTOFieldDefinition.from_field_definition(
            field_definition=FieldDefinition.from_kwarg(
                annotation=int,
                name="a",
            ),
            model_name=ANY,
            default_factory=None,
            dto_field=DTOField(),
            passthrough_constraints=False,
        ),
        replace(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(
                    annotation=int,
                    name="b",
                ),
                model_name=ANY,
                default_factory=None,
                dto_field=DTOField(mark=Mark.READ_ONLY),
            ),
            metadata=ANY,
            type_wrappers=ANY,
            raw=ANY,
            kwarg_definition=ANY,
            passthrough_constraints=False,
        ),
        replace(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(
                    annotation=int,
                    name="c",
                ),
                model_name=ANY,
                default_factory=None,
                dto_field=DTOField(),
            ),
            metadata=ANY,
            type_wrappers=ANY,
            raw=ANY,
            kwarg_definition=ANY,
            passthrough_constraints=False,
        ),
        replace(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(
                    annotation=int,
                    name="d",
                    default=1,
                ),
                model_name=ANY,
                default_factory=None,
                dto_field=DTOField(),
            ),
            metadata=ANY,
            type_wrappers=ANY,
            raw=ANY,
            kwarg_definition=ANY,
            passthrough_constraints=False,
        ),
        replace(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(
                    annotation=Optional[int],
                    name="e",
                ),
                model_name=ANY,
                default_factory=int_factory,
                dto_field=DTOField(),
            ),
            default=None,
            metadata=ANY,
            type_wrappers=ANY,
            raw=ANY,
            kwarg_definition=ANY,
            passthrough_constraints=False,
        ),
    ]


def test_field_definition_generation_v1(
    int_factory: Callable[[], int],
    expected_field_defs: list[DTOFieldDefinition],
) -> None:
    class TestModel(pydantic_v1.BaseModel):
        a: int
        b: Annotated[int, DTOField("read-only")]
        c: Annotated[int, pydantic_v1.Field(gt=1)]
        d: int = pydantic_v1.Field(default=1)
        e: int = pydantic_v1.Field(default_factory=int_factory)

    field_defs = list(PydanticDTO.generate_field_definitions(TestModel))
    assert field_defs[0].model_name == "TestModel"
    for field_def, exp in zip(field_defs, expected_field_defs):
        assert field_def == exp


def test_field_definition_generation_v2(
    int_factory: Callable[[], int],
    expected_field_defs: list[DTOFieldDefinition],
) -> None:
    class TestModel(pydantic_v2.BaseModel):
        a: int
        b: Annotated[int, DTOField("read-only")]
        c: Annotated[int, pydantic_v2.Field(gt=1)]
        d: int = pydantic_v2.Field(default=1)
        e: int = pydantic_v2.Field(default_factory=int_factory)

    field_defs = list(PydanticDTO.generate_field_definitions(TestModel))
    assert field_defs[0].model_name == "TestModel"
    for field_def, exp in zip(field_defs, expected_field_defs):
        assert field_def == exp


def test_detect_nested_field(base_model: type[pydantic_v1.BaseModel | pydantic_v2.BaseModel]) -> None:
    class TestModel(base_model):  # type: ignore[misc, valid-type]
        a: int

    class NotModel:
        pass

    assert PydanticDTO.detect_nested_field(FieldDefinition.from_annotation(TestModel)) is True
    assert PydanticDTO.detect_nested_field(FieldDefinition.from_annotation(NotModel)) is False


ReadOnlyInt = Annotated[int, DTOField("read-only")]


def test_pydantic_dto_annotated_dto_field(base_model: type[pydantic_v1.BaseModel | pydantic_v2.BaseModel]) -> None:
    class Model(base_model):  # type: ignore[misc, valid-type]
        a: Annotated[int, DTOField("read-only")]
        b: ReadOnlyInt

    dto_type = PydanticDTO[Model]
    fields = list(dto_type.generate_field_definitions(Model))
    assert fields[0].dto_field == DTOField("read-only")
    assert fields[1].dto_field == DTOField("read-only")


def test_dto_field_via_pydantic_field_extra_deprecation(
    pydantic_version: PydanticVersion,
) -> None:
    if pydantic_version == "v1":

        class Model(pydantic_v1.BaseModel):  # pyright: ignore
            a: int = pydantic_v1.Field(**dto_field("read-only"))  # type: ignore[arg-type, misc]
    else:

        class Model(pydantic_v2.BaseModel):  # type: ignore[no-redef]
            a: int = pydantic_v2.Field(**dto_field("read-only"))  # type: ignore[call-overload]

    with pytest.warns(DeprecationWarning):
        next(PydanticDTO.generate_field_definitions(Model))
