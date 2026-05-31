from dataclasses import dataclass

from litestar import Litestar, post
from litestar.params import JSONBody


@dataclass
class Item:
    name: str
    price: float


@post("/items")
async def create_item(data: JSONBody[Item]) -> Item:
    return data


app = Litestar(route_handlers=[create_item])
