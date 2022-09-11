from logging import config
from typing import TYPE_CHECKING, Any, Dict, Generator, Iterable, List, Optional, Union

from pydantic import BaseModel
from typing_extensions import Literal


try:
    from picologging import config as picologging_config
except ImportError:
    picologging_config = None


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
    rich_logging: bool = False
    """Whether rich console logging is to be used over the default"""

    def _enable_rich_logging(self, log_config_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Overwrite the default console log configuration with rich log
        configuration.

        Args:
            log_config_dict: dict representation of LoggingConfig model
        Returns:
            dict representation of LoggingConfig model with rich console logging in place of default console logging
        """
        log_config_dict["formatters"]["rich"] = {"format": "%(name)s - %(message)s"}

        log_config_dict["handlers"].pop("console", None)

        log_config_dict["handlers"]["p_rich"] = {
            "class": "rich.logging.RichHandler",
            "level": "DEBUG",
            "rich_tracebacks": True,
            "formatter": "rich",
        }
        if "cfg://handlers.console" in log_config_dict["handlers"]["queue_listener"]["handlers"]:
            log_config_dict["handlers"]["queue_listener"]["handlers"].remove("cfg://handlers.console")

        log_config_dict["handlers"]["queue_listener"]["handlers"].append("cfg://handlers.p_rich")

        return log_config_dict

    def configure(self) -> None:
        """Configured logger with the given configuration.

        If the logger class contains the word `picologging`, we try to
        import and set the dictConfig
        """
        log_config_dict = self.dict(exclude_none=True)

        if self.rich_logging:
            log_config_dict = self._enable_rich_logging(log_config_dict)

        for logging_class in find_keys(self.handlers, "class"):
            if "picologging" in logging_class and picologging_config:
                picologging_config.dictConfig(log_config_dict)
                break
        else:  # no break
            config.dictConfig(log_config_dict)


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
