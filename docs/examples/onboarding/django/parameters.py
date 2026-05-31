from litestar import Litestar, get
from litestar.params import FromPath, FromQuery


@get("/items/{item_id:int}")
async def get_item(item_id: FromPath[int], limit: FromQuery[int]) -> dict[str, int]:
    return {"id": item_id, "limit": limit}


app = Litestar(route_handlers=[get_item])
