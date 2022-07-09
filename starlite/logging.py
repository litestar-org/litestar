from __future__ import annotations

from logging import config
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any

from pydantic import BaseModel
from typing_extensions import Literal


def _resolve_handlers(handlers: list[Any]) -> list[Any]:
    """
    Converts list of string of handlers to the object of respective handler.
    Indexing the list performs the evaluation of the object.
    """
    return [handlers[i] for i in range(len(handlers))]


class QueueListenerHandler(QueueHandler):
    """
    Configures queue listener and handler to support non-blocking logging configuration.
    """

    def __init__(self, handlers: list[Any], respect_handler_level: bool = False, queue: Queue = Queue(-1)):
        super().__init__(queue)
        self.handlers = _resolve_handlers(handlers)
        self._listener: QueueListener = QueueListener(
            self.queue, *self.handlers, respect_handler_level=respect_handler_level
        )
        self._listener.start()


class LoggingConfig(BaseModel):
    version: Literal[1] = 1
    incremental: bool = False
    disable_existing_loggers: bool = False
    filters: dict[str, dict[str, Any]] | None = None
    propagate: bool = True
    formatters: dict[str, dict[str, Any]] = {
        "standard": {"format": "%(levelname)s - %(asctime)s - %(name)s - %(module)s - %(message)s"}
    }
    handlers: dict[str, dict[str, Any]] = {
        "console": {"class": "logging.StreamHandler", "level": "DEBUG", "formatter": "standard"},
        "queue_listener": {"class": "starlite.QueueListenerHandler", "handlers": ["cfg://handlers.console"]},
    }
    loggers: dict[str, dict[str, Any]] = {
        "starlite": {
            "level": "INFO",
            "handlers": ["queue_listener"],
        },
    }
    root: dict[str, dict[str, Any] | list[Any] | str] = {"handlers": ["queue_listener"], "level": "INFO"}

    def configure(self) -> None:
        """Configure logging by converting 'self' to dict and passing it to logging.config.dictConfig"""

        config.dictConfig(self.dict(exclude_none=True))
