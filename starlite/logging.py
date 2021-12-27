from logging import config
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel
from typing_extensions import Literal


class LoggingConfig(BaseModel):
    version: Literal[1] = 1
    incremental: bool = False
    disable_existing_loggers: bool = False
    filters: Optional[Dict[str, Dict[str, Any]]] = None
    formatters: Dict[str, Dict[str, Any]] = {
        "standard": {"format": "%(levelname)s - %(asctime)s - %(name)s - %(module)s - %(message)s"}
    }
    handlers: Dict[str, Dict[str, Any]] = {
        "console": {"class": "logging.StreamHandler", "level": "DEBUG", "formatter": "standard"}
    }
    loggers: Dict[str, Dict[str, Any]] = {
        "starlite": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }
    root: Dict[str, Union[Dict[str, Any], List[Any], str]] = {"handlers": ["console"], "level": "WARNING"}

    def configure(self) -> None:
        """Configure logging by converting 'self' to dict and passing it to logging.config.dictConfig"""

        config.dictConfig(self.dict(exclude_none=True))
