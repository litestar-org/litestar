from dataclasses import dataclass

from litestar import Litestar, post
from litestar.params import JSONBody


@dataclass
class User:
    id: int
    name: str


@post(path="/")
async def index(data: JSONBody[User]) -> User:
    return data


app = Litestar(route_handlers=[index])
