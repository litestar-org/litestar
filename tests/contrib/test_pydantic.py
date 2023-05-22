from __future__ import annotations

from typing import TYPE_CHECKING

from pydantic import BaseModel, Field
from typing_extensions import Annotated

from litestar.contrib.pydantic import PydanticDTO
from litestar.dto.factory import dto_field
from litestar.dto.factory.types import FieldDefinition
from litestar.typing import ParsedType

if TYPE_CHECKING:
    from typing import Callable


def test_field_definition_generation(
    int_factory: Callable[[], int], expected_field_defs: list[FieldDefinition]
) -> None:
    class TestModel(BaseModel):
        a: int
        b: Annotated[int, Field(**dto_field("read-only"))]
        c: Annotated[int, Field(gt=1)]
        d: int = Field(default=1)
        e: int = Field(default_factory=int_factory)

    field_defs = list(PydanticDTO.generate_field_definitions(TestModel))
    assert (
        field_defs[0].unique_model_name
        == "tests.contrib.test_pydantic.test_field_definition_generation.<locals>.TestModel"
    )
    for field_def, exp in zip(field_defs, expected_field_defs):
        assert field_def == exp


def test_detect_nested_field() -> None:
    class TestModel(BaseModel):
        a: int

    class NotModel:
        pass

    assert PydanticDTO.detect_nested_field(ParsedType(TestModel)) is True
    assert PydanticDTO.detect_nested_field(ParsedType(NotModel)) is False
