from litestar import Litestar, Request, post
from litestar.events import listener

SENT_EMAILS: list[tuple[str, str]] = []


async def send_email(email: str, message: str) -> None:
    """Record the email message as sent."""
    SENT_EMAILS.append((email, message))


@listener("user_created", "password_changed")
async def send_email_handler(email: str, message: str) -> None:
    """Send the message to the given email address."""
    await send_email(email, message)


@post("/user-created")
async def create_user_handler(request: Request) -> None:
    """Emit an event for a newly created user."""
    request.app.emit("user_created", email="jane@example.com", message="Welcome aboard!")


@post("/password-changed")
async def password_changed_handler(request: Request) -> None:
    """Emit an event for a changed password."""
    request.app.emit("password_changed", email="jane@example.com", message="Your password was changed.")


app = Litestar(
    route_handlers=[create_user_handler, password_changed_handler],
    listeners=[send_email_handler],
)
