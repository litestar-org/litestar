from __future__ import annotations

from typing import TYPE_CHECKING

import pydantic
import pytest
from pydantic import BaseModel, Field
from typing_extensions import Annotated

from litestar.contrib.pydantic import PydanticDTO
from litestar.dto import dto_field
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from types import ModuleType
    from typing import Callable


def test_field_definition_generation(
    int_factory: Callable[[], int], expected_field_defs: list[DTOFieldDefinition]
) -> None:
    class TestModel(BaseModel):
        a: int
        b: Annotated[int, Field(**dto_field("read-only"))]  # pyright: ignore
        c: Annotated[int, Field(gt=1)]
        d: int = Field(default=1)
        e: int = Field(default_factory=int_factory)

    field_defs = list(PydanticDTO.generate_field_definitions(TestModel))
    assert field_defs[0].model_name == "TestModel"
    for field_def, exp in zip(field_defs, expected_field_defs):
        assert field_def == exp


def test_detect_nested_field() -> None:
    class TestModel(BaseModel):
        a: int

    class NotModel:
        pass

    assert PydanticDTO.detect_nested_field(FieldDefinition.from_annotation(TestModel)) is True
    assert PydanticDTO.detect_nested_field(FieldDefinition.from_annotation(NotModel)) is False


@pytest.mark.skipif(pydantic.VERSION.startswith("2"), reason="Beanie does not support pydantic 2 yet")
def test_generate_field_definitions_from_beanie_models(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from typing import Optional

import pymongo
from pydantic import BaseModel

from beanie import Document


class Category(BaseModel):
    name: str
    description: str


class Product(Document):  # This is the model
    name: str
    description: Optional[str] = None
    price: float
    category: Category
"""
    )
    field_names = [field.name for field in PydanticDTO.generate_field_definitions(module.Product)]
    assert field_names == ["id", "revision_id", "name", "description", "price", "category"]
