from logging import config
from typing import Dict, Optional, Union

from pydantic import BaseModel
from typing_extensions import Literal


class LoggingConfig(BaseModel):
    version: Literal[1] = 1
    incremental: bool = False
    disable_existing_loggers: bool = False
    filters: Optional[Dict[str, dict]] = None
    formatters: Dict[str, dict] = {
        "standard": {"format": "%(levelname)s - %(asctime)s - %(name)s - %(module)s - %(message)s"}
    }
    handlers: Dict[str, dict] = {
        "console": {"class": "logging.StreamHandler", "level": "DEBUG", "formatter": "standard"}
    }
    loggers: Dict[str, dict] = {
        "starlite": {
            "level": "INFO",
            "handlers": ["console"],
        },
    }
    root: Dict[str, Union[dict, list, str]] = {"handlers": ["console"], "level": "WARNING"}

    def configure(self):
        """Configure logging by converting 'self' to dict and passing it to logging.config.dictConfig"""

        config.dictConfig(self.dict(exclude_none=True))
