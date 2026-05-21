import logging

from litestar import Litestar, Response, get
from litestar.background_tasks import BackgroundTask

logger = logging.getLogger(__name__)


async def send_welcome_email(address: str) -> None:
    logger.info("sent welcome email to %s", address)


@get("/signup")
async def signup() -> Response[dict[str, str]]:
    return Response(
        {"status": "queued"},
        background=BackgroundTask(send_welcome_email, "user@example.com"),
    )


app = Litestar(route_handlers=[signup])
