from importlib.util import find_spec
from typing import Any, Callable, Dict, List, Optional, Union

from orjson import dumps
from pydantic import BaseModel, Field
from typing_extensions import Literal

from starlite.exceptions import (
    ImproperlyConfiguredException,
    MissingDependencyException,
)
from starlite.types import Logger

default_handlers: Dict[str, Dict[str, Any]] = {
    "console": {
        "class": "logging.StreamHandler",
        "level": "DEBUG",
        "formatter": "standard",
    },
    "queue_listener": {
        "class": "starlite.logging.standard.QueueListenerHandler",
        "handlers": ["cfg://handlers.console"],
    },
}

default_picologging_handlers: Dict[str, Dict[str, Any]] = {
    "console": {
        "class": "picologging.StreamHandler",
        "level": "DEBUG",
        "formatter": "standard",
    },
    "queue_listener": {
        "class": "starlite.logging.picologging.QueueListenerHandler",
        "handlers": ["cfg://handlers.console"],
    },
}


def set_default_handlers() -> Dict[str, Dict[str, Any]]:
    """

    Returns:
        The default handlers for the config.
    """
    if find_spec("picologging"):
        return default_picologging_handlers
    return default_handlers


def get_logger_placeholder(_: str) -> Any:
    """
    Raises:
        ImproperlyConfiguredException
    """
    raise ImproperlyConfiguredException("'logging_config.configure' must be called before calling 'get_logger'")


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
    handlers: Dict[str, Dict[str, Any]] = Field(default_factory=set_default_handlers)
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
    get_logger: Callable[[str], Logger] = get_logger_placeholder
    """A function that returns a logger. E.g. the stdlib 'getLogger'."""

    def configure(self) -> None:
        """Configured logger with the given configuration.

        If the logger class contains the word `picologging`, we try to
        import and set the dictConfig
        """
        try:
            if "picologging" in str(dumps(self.handlers)):

                from picologging import (  # pylint: disable=import-outside-toplevel
                    config,
                    getLogger,
                )
            else:
                from logging import (  # type: ignore[no-redef]  # pylint: disable=import-outside-toplevel
                    config,
                    getLogger,
                )
            config.dictConfig(self.dict(exclude_none=True))
            self.get_logger = getLogger  # type: ignore
        except ImportError as e:  # pragma: no cover
            raise MissingDependencyException("picologging is not installed") from e
