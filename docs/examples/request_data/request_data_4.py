from dataclasses import dataclass

from litestar import Litestar, post
from litestar.params import URLEncodedBody


@dataclass
class User:
    id: int
    name: str


@post(path="/")
async def create_user(data: URLEncodedBody[User]) -> User:
    return data


app = Litestar(route_handlers=[create_user])
