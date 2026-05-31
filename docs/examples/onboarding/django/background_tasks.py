import logging

from litestar import Litestar, Response, post
from litestar.background_tasks import BackgroundTask

logger = logging.getLogger(__name__)


async def send_welcome_email(address: str) -> None:
    logger.info("sending welcome email to %s", address)


@post("/signup")
async def signup(data: dict[str, str]) -> Response[dict[str, str]]:
    return Response(
        {"status": "queued"},
        background=BackgroundTask(send_welcome_email, data["email"]),
    )


app = Litestar(route_handlers=[signup])
