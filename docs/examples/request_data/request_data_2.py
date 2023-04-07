from dataclasses import dataclass

from litestar import Litestar, post


@dataclass
class User:
    id: int
    name: str


@post(path="/")
async def index(data: User) -> User:
    return data


app = Litestar(route_handlers=[index])
