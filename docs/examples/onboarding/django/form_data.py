from dataclasses import dataclass

from litestar import Litestar, post
from litestar.params import URLEncodedBody


@dataclass
class LoginForm:
    username: str
    password: str


@post("/login")
async def login(data: URLEncodedBody[LoginForm]) -> dict[str, str]:
    return {"user": data.username}


app = Litestar(route_handlers=[login])
