from atexit import register
from logging import config
from logging.handlers import QueueHandler, QueueListener
from queue import Queue
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel
from typing_extensions import Literal


def _resolve_handlers(handlers: List[Any]) -> List[Any]:
    """
    Converts list of string of handlers to the object of respective handler.
    Indexing the list performs the evaluation of the object.
    """
    return [handlers[i] for i in range(len(handlers))]


class QueueListenerHandler(QueueHandler):
    """
    Configures queue listener and handler to support non-blocking logging configuration.
    """

    def __init__(
        self, handlers: List[Any], respect_handler_level: bool = False, auto_run: bool = True, queue: Queue = Queue(-1)
    ):
        super().__init__(queue)
        self.handlers = _resolve_handlers(handlers)
        self._listener: QueueListener = QueueListener(
            self.queue, *self.handlers, respect_handler_level=respect_handler_level
        )
        if auto_run:
            self.start()
            register(self.stop)

    def start(self) -> None:
        """
        starts the listener.
        """
        self._listener.start()

    def stop(self) -> None:
        """
        Manually stop a listener.
        """
        self._listener.stop()


class LoggingConfig(BaseModel):
    version: Literal[1] = 1
    incremental: bool = False
    disable_existing_loggers: bool = False
    filters: Optional[Dict[str, Dict[str, Any]]] = None
    formatters: Dict[str, Dict[str, Any]] = {
        "standard": {"format": "%(levelname)s - %(asctime)s - %(name)s - %(module)s - %(message)s"}
    }
    handlers: Dict[str, Dict[str, Any]] = {
        "console": {"class": "logging.StreamHandler", "level": "DEBUG", "formatter": "standard"},
        "queue_listener": {"class": "starlite.QueueListenerHandler", "handlers": ["cfg://handlers.console"]},
    }
    loggers: Dict[str, Dict[str, Any]] = {
        "starlite": {
            "level": "INFO",
            "handlers": ["queue_listener"],
        },
    }
    root: Dict[str, Union[Dict[str, Any], List[Any], str]] = {"handlers": ["console"], "level": "WARNING"}

    def configure(self) -> None:
        """Configure logging by converting 'self' to dict and passing it to logging.config.dictConfig"""

        config.dictConfig(self.dict(exclude_none=True))
