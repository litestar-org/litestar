from typing import Annotated

from msgspec import Meta, Struct

from litestar import Litestar, get


class Stock(Struct):
    """Stock level of a product."""

    sku: Annotated[str, Meta(pattern="^[A-Z]{3}-[0-9]{4}$", examples=["CHR-0001"])]
    quantity: Annotated[int, Meta(ge=0, description="Units in the warehouse")]
    warehouse: Annotated[str | None, Meta(extra_json_schema={"deprecated": True})] = None


@get("/stock", sync_to_thread=False)
def get_stock() -> Stock:
    return Stock(sku="CHR-0001", quantity=12)


app = Litestar(route_handlers=[get_stock])
