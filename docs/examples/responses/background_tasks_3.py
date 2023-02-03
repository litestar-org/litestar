import logging
from typing import Dict

from starlite import Response, Starlite, get
from starlite.background_tasks import BackgroundTask, BackgroundTasks

logger = logging.getLogger(__name__)
greeted = set()


async def logging_task(name: str) -> None:
    logger.info("%s was greeted", name)


async def saving_task(name: str) -> None:
    greeted.add(name)


@get("/")
def greeter(name: str) -> Response[Dict[str, str]]:
    return Response(
        {"hello": name},
        background=BackgroundTasks(
            [
                BackgroundTask(logging_task, name),
                BackgroundTask(saving_task, name),
            ]
        ),
    )


app = Starlite(route_handlers=[greeter])
