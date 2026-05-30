from dataclasses import dataclass

from litestar import Litestar, Request, post
from litestar.events import listener


@dataclass
class User:
    id: int
    email: str


@listener("user_created")
async def send_welcome_email(user: User) -> None:
    # Real implementations would send a message; the test asserts the handler ran.
    print(f"welcome {user.email}")


@post("/users")
async def create_user(data: User, request: Request) -> User:
    request.app.emit("user_created", user=data)
    return data


app = Litestar(route_handlers=[create_user], listeners=[send_welcome_email])
