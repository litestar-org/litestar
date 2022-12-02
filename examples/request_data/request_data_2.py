from starlite import post, Starlite

from dataclasses import dataclass


@dataclass
class User:
    id: int
    name: str


@post(path="/")
async def index(data: User) -> User:
    return data


app = Starlite(route_handlers=[index])
