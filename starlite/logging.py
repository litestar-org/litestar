from logging import config
from queue import Queue
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel
from typing_extensions import Literal

try:
    from picologging import Logger, StreamHandler
    from picologging import getLogger as _getLogger
    from picologging.handlers import QueueHandler, QueueListener
except ImportError:
    from logging import Logger, StreamHandler
    from logging import getLogger as _getLogger
    from logging.handlers import QueueHandler, QueueListener


def _resolve_handlers(handlers: List[Any]) -> List[Any]:
    """
    Converts list of string of handlers to the object of respective handler.
    Indexing the list performs the evaluation of the object.
    """
    return [handlers[i] for i in range(len(handlers))]


class QueueListenerHandler(QueueHandler):  # type: ignore
    """
    Configures queue listener and handler to support non-blocking logging configuration.
    """

    def __init__(self, handlers: List[Any], respect_handler_level: bool = False, queue: Queue = Queue(-1)):
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
    filters: Optional[Dict[str, Dict[str, Any]]] = None
    propagate: bool = True
    formatters: Dict[str, Dict[str, Any]] = {
        "standard": {"format": "%(levelname)s - %(asctime)s - %(name)s - %(module)s - %(message)s"}
    }
    handlers: Dict[str, Dict[str, Any]] = {
        "console": {"class": StreamHandler.__qualname__, "level": "DEBUG", "formatter": "standard"},
        "queue_listener": {"class": "starlite.QueueListenerHandler", "handlers": ["cfg://handlers.console"]},
    }
    loggers: Dict[str, Dict[str, Any]] = {
        "starlite": {
            "level": "INFO",
            "handlers": ["queue_listener"],
        },
    }
    root: Dict[str, Union[Dict[str, Any], List[Any], str]] = {"handlers": ["queue_listener"], "level": "INFO"}

    def configure(self) -> None:
        """Configured logger with the given configuration."""
        config.dictConfig(self.dict(exclude_none=True))


def getLogger(name: str) -> Logger:
    """Helper method to return the configured logger

    Returns:
        Logger: Returns a configured logger or picologging instance.
    """

    return _getLogger(name)
