import logging
from typing import Dict

from starlite import Starlite, get
from starlite.background_tasks import BackgroundTask

logger = logging.getLogger(__name__)


async def logging_task(identifier: str, message: str) -> None:
    logger.info("%s: %s", identifier, message)


@get("/", background=BackgroundTask(logging_task, "greeter", message="was called"))
def greeter() -> Dict[str, str]:
    return {"hello": "world"}


app = Starlite(route_handlers=[greeter])
