import logging
from asyncio import sleep
from datetime import datetime

from litestar import Litestar

logger = logging.getLogger()


async def shutdown_callable() -> None:
    """Function called during 'on_shutdown'."""
    await sleep(0.5)


def before_shutdown_handler(app_instance: Litestar) -> None:
    """Function called before 'on_shutdown'."""
    start_time = datetime.now()
    app_instance.state.start_time = start_time.timestamp()
    logger.info("shutdown sequence begin at %s", start_time.isoformat())


def after_shutdown_handler(app_instance: Litestar) -> None:
    """Function called after 'on_shutdown'."""
    logger.info(
        "shutdown sequence ended at: %s, time elapsed: %d",
        datetime.now().isoformat(),
        datetime.now().timestamp() - app_instance.state.start_time,
    )


app = Litestar(
    on_shutdown=[shutdown_callable],
    before_shutdown=[before_shutdown_handler],
    after_shutdown=[after_shutdown_handler],
)
