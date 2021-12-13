from logging import config
from typing import Dict, Literal, Optional, Union

from pydantic import BaseModel


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

    def configure(self, debug: bool = False):
        """Configure logging by converting 'self' to dict and passing it to logging.config.dictConfig"""
        logging_config = self.dict(exclude_none=True)
        if debug and "starlite" in logging_config["loggers"]:
            logging_config["loggers"]["starlite"]["level"] = "DEBUG"
        config.dictConfig(logging_config)
