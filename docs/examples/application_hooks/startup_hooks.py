import logging
from asyncio import sleep
from datetime import datetime

from starlite import Starlite

logger = logging.getLogger()


async def startup_callable() -> None:
    """Function called during 'on_startup'."""
    await sleep(0.5)


def before_startup_handler(app_instance: Starlite) -> None:
    """Function called before 'on_startup'."""
    start_time = datetime.now()
    app_instance.state.start_time = start_time.timestamp()
    logger.info("startup sequence begin at %s", start_time.isoformat())


def after_startup_handler(app_instance: Starlite) -> None:
    """Function called after 'on_startup'."""
    logger.info(
        "startup sequence ended at: %s, time elapsed: %d",
        datetime.now().isoformat(),
        datetime.now().timestamp() - app_instance.state.start_time,
    )


app = Starlite(
    on_startup=[startup_callable],
    before_startup=[before_startup_handler],
    after_startup=[after_startup_handler],
)
