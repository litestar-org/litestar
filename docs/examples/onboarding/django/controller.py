from litestar import Controller, Litestar, delete, get, patch, post
from litestar.params import FromPath


class ItemController(Controller):
    path = "/items"

    @get("/")
    async def list_items(self) -> list[dict[str, int]]:
        return [{"id": 1}, {"id": 2}]

    @post("/")
    async def create_item(self, data: dict[str, str]) -> dict[str, str]:
        return data

    @get("/{item_id:int}")
    async def get_item(self, item_id: FromPath[int]) -> dict[str, int]:
        return {"id": item_id}

    @patch("/{item_id:int}")
    async def update_item(self, item_id: FromPath[int], data: dict[str, str]) -> dict[str, object]:
        return {"id": item_id, **data}

    @delete("/{item_id:int}")
    async def delete_item(self, item_id: FromPath[int]) -> None:
        return None


app = Litestar(route_handlers=[ItemController])
