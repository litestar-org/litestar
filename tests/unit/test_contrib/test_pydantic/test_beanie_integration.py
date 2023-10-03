from typing import Optional

import beanie
import pydantic

from litestar.contrib.pydantic import PydanticDTO


def test_generate_field_definitions_from_beanie_models() -> None:
    class Category(pydantic.BaseModel):
        name: str
        description: str

    class Product(beanie.Document):
        name: str
        description: Optional[str] = None
        price: float
        category: Category

    field_names = [field.name for field in PydanticDTO.generate_field_definitions(Product)]
    assert field_names == ["id", "revision_id", "name", "description", "price", "category"]
