from logging import config
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel
from typing_extensions import Literal

from starlite.logging.standard import QueueListenerHandler


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
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "standard",
        },
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


__all__ = ["LoggingConfig", "QueueListenerHandler"]
