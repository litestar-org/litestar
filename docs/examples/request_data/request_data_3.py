from dataclasses import dataclass

from starlite import Starlite, post
from starlite.params import Body


@dataclass
class User:
    id: int
    name: str


@post(path="/")
async def create_user(
    data: User = Body(title="Create User", description="Create a new user."),
) -> User:
    return data


app = Starlite(route_handlers=[create_user])
