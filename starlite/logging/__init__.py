from logging import config
from typing import Any, Dict, Generator, Iterable, List, Optional, Union

from pydantic import BaseModel
from typing_extensions import Literal

from starlite.logging.standard import QueueListenerHandler

try:
    from picologging import config as picologging_config
except ImportError:
    picologging_config = None

__all__ = ["LoggingConfig", "QueueListenerHandler"]


class LoggingConfig(BaseModel):
    """Convenience `pydantic` model for configuring logging.

    For detailed instructions consult [standard library docs](https://docs.python.org/3/library/logging.config.html).
    """

    version: Literal[1] = 1
    """The only valid value at present is 1."""
    incremental: bool = False
    """Whether the configuration is to be interpreted as incremental to the existing configuration. """
    disable_existing_loggers: bool = False
    """Whether any existing non-root loggers are to be disabled."""
    filters: Optional[Dict[str, Dict[str, Any]]] = None
    """A dict in which each key is a filter id and each value is a dict describing how to configure the corresponding Filter instance."""
    propagate: bool = True
    """If messages must propagate to handlers higher up the logger hierarchy from this logger."""
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
    """A dict in which each key is a handler id and each value is a dict describing how to configure the corresponding Handler instance."""
    loggers: Dict[str, Dict[str, Any]] = {
        "starlite": {
            "level": "INFO",
            "handlers": ["queue_listener"],
        },
    }
    """A dict in which each key is a logger name and each value is a dict describing how to configure the corresponding Logger instance."""
    root: Dict[str, Union[Dict[str, Any], List[Any], str]] = {"handlers": ["queue_listener"], "level": "INFO"}
    """This will be the configuration for the root logger. Processing of the configuration will be as for any logger,
    except that the propagate setting will not be applicable."""

    def configure(self) -> None:
        """Configured logger with the given configuration.

        If the logger class contains the word `picologging`, we try to
        import and set the dictConfig
        """
        for logging_class in find_keys(self.handlers, "class"):
            if "picologging" in logging_class and picologging_config:
                picologging_config.dictConfig(self.dict(exclude_none=True))
                break
        config.dictConfig(self.dict(exclude_none=True))


def find_keys(node: Union[List, Dict], key: str) -> Generator[Iterable, None, None]:
    """Find Nested Keys with name
    Search a dictionary for the presence of key
    Args:
        node (Union[List, Dict]): a dictionary to search
        key (str): the dictionary key to find

    Yields:
        Generator[Iterable, None, None]: Value of dictionary key
    """
    if isinstance(node, list):
        for list_entry in node:
            yield from find_keys(list_entry, key)
    elif isinstance(node, dict):
        if key in node:
            yield node[key]
        for dict_entry in node.values():
            yield from find_keys(dict_entry, key)
