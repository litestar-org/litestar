from dataclasses import dataclass

from litestar import Litestar, Request, post
from litestar.events import listener

SENT_WELCOME_EMAILS: list[str] = []


async def send_welcome_mail(email: str) -> None:
    """Record the welcome email as sent."""
    SENT_WELCOME_EMAILS.append(email)


@listener("user_created")
async def send_welcome_email_handler(email: str) -> None:
    """Send a welcome email to the given address."""
    await send_welcome_mail(email)


@dataclass
class CreateUserDTO:
    first_name: str
    last_name: str
    email: str


@post("/users")
async def create_user_handler(data: CreateUserDTO, request: Request) -> None:
    """Create a new user and emit an event.

    Assuming we have now created a user, we want to send a welcome email.
    To do this in a non-blocking fashion, we emit an event to a listener,
    which sends the email without slowing down the response cycle.
    """
    request.app.emit("user_created", email=data.email)


app = Litestar(route_handlers=[create_user_handler], listeners=[send_welcome_email_handler])
