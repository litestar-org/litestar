from typing import TYPE_CHECKING, Optional, Type

import beanie

if TYPE_CHECKING:
    from pydantic import BaseModel

from litestar.contrib.pydantic import PydanticDTO


def test_generate_field_definitions_from_beanie_models(base_model: "Type[BaseModel]") -> None:
    class Category(base_model):  # type: ignore[valid-type, misc]
        name: str
        description: str

    class Product(beanie.Document):
        name: str
        description: Optional[str] = None
        price: float
        category: Category

    field_names = [field.name for field in PydanticDTO.generate_field_definitions(Product)]
    assert field_names == ["id", "revision_id", "name", "description", "price", "category"]
