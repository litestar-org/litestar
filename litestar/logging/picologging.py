from __future__ import annotations

import dataclasses
import queue
from typing import TYPE_CHECKING, Any

import picologging
from picologging.handlers import QueueHandler, QueueListener

from litestar.logging.config import LoggingConfig

if TYPE_CHECKING:
    from litestar import Litestar
    from litestar.types import LifespanHook, Logger


@dataclasses.dataclass(frozen=True)
class PicoLoggingConfig(LoggingConfig):
    def configure_handlers(self, app: Litestar, logger: Logger) -> LifespanHook:
        if not isinstance(logger, picologging.Logger):
            raise ValueError(f"Cannot configure logger of type {type(logger)!r}")

        handler_queue: queue.Queue[Any] = queue.Queue(-1)
        queue_handler = QueueHandler(handler_queue)
        for handler in logger.handlers:
            logger.removeHandler(handler)
        logger.addHandler(queue_handler)
        listener = QueueListener(handler_queue, queue_handler, respect_handler_level=True)
        listener.start()

        def shutdown(app: Litestar) -> None:
            listener.stop()

        return shutdown
