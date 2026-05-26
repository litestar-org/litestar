import logging

from litestar import Litestar, Response, get
from litestar.background_tasks import BackgroundTask

logger = logging.getLogger(__name__)


async def log_visit(name: str) -> None:
    logger.info("greeted %s", name)


@get("/")
async def greeter() -> Response[dict[str, str]]:
    return Response(
        {"hello": "world"},
        background=BackgroundTask(log_visit, "world"),
    )


app = Litestar(route_handlers=[greeter])
