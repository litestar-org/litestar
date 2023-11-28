from __future__ import annotations

from dataclasses import replace
from typing import TYPE_CHECKING
from unittest.mock import ANY

import pytest

from litestar.dto import DTOField, Mark
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from typing import Callable


@pytest.fixture
def int_factory() -> Callable[[], int]:
    return lambda: 2


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
        ),
        replace(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(
                    annotation=int,
                    name="e",
                ),
                model_name=ANY,
                default_factory=int_factory,
                dto_field=DTOField(),
            ),
            metadata=ANY,
            type_wrappers=ANY,
            raw=ANY,
            kwarg_definition=ANY,
        ),
    ]
