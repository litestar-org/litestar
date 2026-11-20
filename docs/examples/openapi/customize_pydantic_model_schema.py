from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, WithJsonSchema, computed_field

from litestar import Litestar, post
from litestar.params import JSONBody


class Product(BaseModel):
    """A product in the catalogue."""

    model_config = ConfigDict(json_schema_extra={"examples": [{"name": "Chair", "price": 4900, "sku": "CHR-0001"}]})

    name: str = Field(description="Display name", max_length=50)
    sku: Annotated[str, WithJsonSchema({"type": "string", "pattern": "^[A-Z]{3}-[0-9]{4}$"})]
    price: int = Field(gt=0, description="Price in cents")

    @computed_field
    @property
    def label(self) -> str:
        return f"{self.name} ({self.sku})"


@post("/products", sync_to_thread=False)
def create_product(data: JSONBody[Product]) -> Product:
    return data


app = Litestar(route_handlers=[create_product])
