from typing import Optional

import pydantic
import pytest

from litestar.contrib.pydantic import PydanticDTO


@pytest.mark.skipif(pydantic.VERSION.startswith("2"), reason="Beanie does not support pydantic 2 yet")
def test_generate_field_definitions_from_beanie_models() -> None:
    pytest.importorskip("pymongo")
    beanie = pytest.importorskip("beanie")

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
