from litestar import Litestar, get
from litestar.openapi.config import OpenAPIConfig
from litestar.params import FromPath


@get(
    "/items/{item_id:int}",
    tags=["items"],
    summary="Retrieve an item",
    description="Look up a single item by its numeric identifier.",
    operation_id="get_item_by_id",
)
async def get_item(item_id: FromPath[int]) -> dict[str, int]:
    return {"id": item_id}


app = Litestar(
    route_handlers=[get_item],
    openapi_config=OpenAPIConfig(title="Items API", version="1.0.0"),
)
