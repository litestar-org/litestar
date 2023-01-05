import logging

from starlite import BackgroundTask, Starlite, get

logger = logging.getLogger(__name__)


async def logging_task(identifier: str, message: str) -> None:
    logger.info(f"{identifier}: {message}")


@get("/", background=BackgroundTask(logging_task, "greeter", message="was called"))
def greeter() -> dict[str, str]:
    return {"hello": "world"}


app = Starlite(route_handlers=[greeter])
