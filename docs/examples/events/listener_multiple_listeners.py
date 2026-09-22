from dataclasses import dataclass
from typing import Any

from litestar import Litestar, Request, post
from litestar.events import listener

SENT_FAREWELL_EMAILS: list[str] = []
SUPPORT_TICKETS: list[str] = []


@listener("user_deleted")
async def send_farewell_email_handler(email: str, **kwargs: Any) -> None:
    """Send a farewell email to the given address.

    The ``**kwargs`` catch-all absorbs the other keyword arguments passed
    to ``emit``, which this listener is not interested in.
    """
    SENT_FAREWELL_EMAILS.append(email)


@listener("user_deleted")
async def notify_customer_support(reason: str, **kwargs: Any) -> None:
    """Open a ticket with customer support for the given reason."""
    SUPPORT_TICKETS.append(reason)


@dataclass
class DeleteUserDTO:
    email: str
    reason: str


@post("/users")
async def delete_user_handler(data: DeleteUserDTO, request: Request) -> None:
    """Delete a user and emit an event handled by multiple listeners."""
    request.app.emit("user_deleted", email=data.email, reason=data.reason)


app = Litestar(
    route_handlers=[delete_user_handler],
    listeners=[send_farewell_email_handler, notify_customer_support],
)
