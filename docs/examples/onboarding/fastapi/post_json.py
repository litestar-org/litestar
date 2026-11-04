from pydantic import BaseModel

from litestar import Litestar, post
from litestar.params import JSONBody


class Item(BaseModel):
    name: str


@post("/items/")
async def create_item(data: JSONBody[Item]) -> dict[str, str]:
    return {"name": data.name}


app = Litestar(route_handlers=[create_item])
