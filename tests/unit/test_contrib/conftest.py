from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import ANY

import pytest

from litestar.dto.factory import DTOField
from litestar.dto.factory.data_structures import FieldDefinition
from litestar.types.empty import Empty
from litestar.typing import ParsedType

if TYPE_CHECKING:
    from typing import Callable


@pytest.fixture
def int_factory() -> Callable[[], int]:
    return lambda: 2


@pytest.fixture
def expected_field_defs(int_factory: Callable[[], int]) -> list[FieldDefinition]:
    return [
        FieldDefinition(
            name="a",
            default=Empty,
            parsed_type=ParsedType(int),
            unique_model_name=ANY,
            default_factory=Empty,
            dto_field=DTOField(),
            dto_for=None,
        ),
        FieldDefinition(
            name="b",
            default=Empty,
            parsed_type=ParsedType(int),
            unique_model_name=ANY,
            default_factory=Empty,
            dto_field=DTOField(mark="read-only"),
            dto_for=None,
        ),
        FieldDefinition(
            name="c",
            default=Empty,
            parsed_type=ParsedType(int),
            unique_model_name=ANY,
            default_factory=Empty,
            dto_field=DTOField(),
            dto_for=None,
        ),
        FieldDefinition(
            name="d",
            default=1,
            parsed_type=ParsedType(int),
            unique_model_name=ANY,
            default_factory=Empty,
            dto_field=DTOField(),
            dto_for=None,
        ),
        FieldDefinition(
            name="e",
            default=Empty,
            parsed_type=ParsedType(int),
            unique_model_name=ANY,
            default_factory=int_factory,
            dto_field=DTOField(),
            dto_for=None,
        ),
    ]
