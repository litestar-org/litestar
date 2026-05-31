from litestar import Litestar, Router, get
from litestar.params import FromPath


@get("/")
async def list_items() -> list[dict[str, int]]:
    return [{"id": 1}]


@get("/{item_id:int}")
async def get_item(item_id: FromPath[int]) -> dict[str, int]:
    return {"id": item_id}


items_router = Router(path="/items", route_handlers=[list_items, get_item])
api_router = Router(path="/api/v1", route_handlers=[items_router])

app = Litestar(route_handlers=[api_router])
