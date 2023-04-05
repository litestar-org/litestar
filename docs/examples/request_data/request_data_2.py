from dataclasses import dataclass

from starlite import Starlite, post


@dataclass
class User:
    id: int
    name: str


@post(path="/")
async def index(data: User) -> User:
    return data


app = Starlite(route_handlers=[index])
