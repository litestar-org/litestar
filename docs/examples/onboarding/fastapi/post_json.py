from pydantic import BaseModel

from litestar import Litestar, post


class Item(BaseModel):
    name: str


@post("/items/")
async def create_item(data: Item) -> dict[str, str]:
    return {"name": data.name}


app = Litestar(route_handlers=[create_item])
