from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from importlib.util import find_spec
from logging import INFO
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

from starlite.exceptions import (
    ImproperlyConfiguredException,
    MissingDependencyException,
)
from starlite.serialization import encode_json

if TYPE_CHECKING:
    from typing import NoReturn

    from starlite.types import Logger
    from starlite.types.callable_types import GetLogger

try:
    from structlog.types import BindableLogger, Processor, WrappedLogger
except ImportError:
    BindableLogger = Any  # type: ignore
    Processor = Any  # type: ignore
    WrappedLogger = Any  # type: ignore


default_handlers: dict[str, dict[str, Any]] = {
    "console": {
        "class": "logging.StreamHandler",
        "level": "DEBUG",
        "formatter": "standard",
    },
    "queue_listener": {
        "class": "starlite.logging.standard.QueueListenerHandler",
        "level": "DEBUG",
        "formatter": "standard",
    },
}

default_picologging_handlers: dict[str, dict[str, Any]] = {
    "console": {
        "class": "picologging.StreamHandler",
        "level": "DEBUG",
        "formatter": "standard",
    },
    "queue_listener": {
        "class": "starlite.logging.picologging.QueueListenerHandler",
        "level": "DEBUG",
        "formatter": "standard",
    },
}


def get_default_handlers() -> dict[str, dict[str, Any]]:
    """Return the default logging handlers for the config.

    Returns:
        A dictionary of logging handlers
    """
    if find_spec("picologging"):
        return default_picologging_handlers
    return default_handlers


def get_logger_placeholder(_: str) -> NoReturn:  # pragma: no cover
    """Raise an `ImproperlyConfiguredException."""
    raise ImproperlyConfiguredException(
        "To use 'app.get_logger', 'request.get_logger' or 'socket.get_logger' pass 'logging_config' to the Starlite constructor"
    )


class BaseLoggingConfig(ABC):  # pragma: no cover
    """Abstract class that should be extended by logging configs."""

    __slots__ = ()

    @abstractmethod
    def configure(self) -> GetLogger:
        """Return logger with the given configuration.

        Returns:
            A 'logging.getLogger' like function.
        """
        raise NotImplementedError("abstract method")


@dataclass
class LoggingConfig(BaseLoggingConfig):
    """Configuration class for standard logging.

    Notes:
        - If 'picologging' is installed it will be used by default.
    """

    version: Literal[1] = field(default=1)
    """The only valid value at present is 1."""
    incremental: bool = field(default=False)
    """Whether the configuration is to be interpreted as incremental to the existing configuration.

    Notes:
        - This option is ignored for 'picologging'
    """
    disable_existing_loggers: bool = field(default=False)
    """Whether any existing non-root loggers are to be disabled."""
    filters: dict[str, dict[str, Any]] | None = field(default=None)
    """A dict in which each key is a filter id and each value is a dict describing how to configure the corresponding
    Filter instance.
    """
    propagate: bool = field(default=True)
    """If messages must propagate to handlers higher up the logger hierarchy from this logger."""
    formatters: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "standard": {"format": "%(levelname)s - %(asctime)s - %(name)s - %(module)s - %(message)s"}
        }
    )
    handlers: dict[str, dict[str, Any]] = field(default_factory=get_default_handlers)
    """A dict in which each key is a handler id and each value is a dict describing how to configure the corresponding
    Handler instance.
    """
    loggers: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "starlite": {"level": "INFO", "handlers": ["queue_listener"], "propagate": False},
        }
    )
    """A dict in which each key is a logger name and each value is a dict describing how to configure the corresponding
    Logger instance.
    """
    root: dict[str, dict[str, Any] | list[Any] | str] = field(
        default_factory=lambda: {
            "handlers": ["queue_listener"],
            "level": "INFO",
        }
    )
    """This will be the configuration for the root logger.

    Processing of the configuration will be as for any logger, except that the propagate setting will not be applicable.
    """

    def __post_init__(self) -> None:
        if "queue_listener" not in self.handlers:
            self.handlers["queue_listener"] = get_default_handlers()["queue_listener"]

        if "starlite" not in self.loggers:
            self.loggers["starlite"] = {
                "level": "INFO",
                "handlers": ["queue_listener"],
                "propagate": False,
            }

    def configure(self) -> GetLogger:
        """Return logger with the given configuration.

        Returns:
            A 'logging.getLogger' like function.
        """

        if "picologging" in str(encode_json(self.handlers)):
            try:
                from picologging import config, getLogger
            except ImportError as e:  # pragma: no cover
                raise MissingDependencyException("picologging is not installed") from e

            values = {k: v for k, v in asdict(self).items() if v is not None and k != "incremental"}
        else:
            from logging import config, getLogger  # type: ignore[no-redef, assignment]

            values = {k: v for k, v in asdict(self).items() if v is not None}

        config.dictConfig(values)
        return cast("Callable[[str], Logger]", getLogger)


def default_structlog_processors() -> list[Processor] | None:  # pyright: ignore
    """Set the default processors for structlog.

    Returns:
        An optional list of processors.
    """
    try:
        import structlog

        return [
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.format_exc_info,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(serializer=encode_json),
        ]
    except ImportError:  # pragma: no cover
        return None


def default_wrapper_class() -> type[BindableLogger] | None:  # pyright: ignore
    """Set the default wrapper class for structlog.

    Returns:
        An optional wrapper class.
    """

    try:
        import structlog

        return structlog.make_filtering_bound_logger(INFO)
    except ImportError:  # pragma: no cover
        return None


def default_logger_factory() -> Callable[..., WrappedLogger] | None:
    """Set the default logger factory for structlog.

    Returns:
        An optional logger factory.
    """
    try:
        import structlog

        return structlog.BytesLoggerFactory()
    except ImportError:  # pragma: no cover
        return None


@dataclass
class StructLoggingConfig(BaseLoggingConfig):
    """Configuration class for structlog.

    Notes:
        - requires 'structlog' to be installed.
    """

    processors: list[Processor] | None = field(default_factory=default_structlog_processors)  # pyright: ignore
    """Iterable of structlog logging processors."""
    wrapper_class: type[BindableLogger] | None = field(default_factory=default_wrapper_class)  # pyright: ignore
    """Structlog bindable logger."""
    context_class: dict[str, Any] | None = None
    """Context class (a 'contextvar' context) for the logger."""
    logger_factory: Callable[..., WrappedLogger] | None = field(default_factory=default_logger_factory)
    """Logger factory to use."""
    cache_logger_on_first_use: bool = field(default=True)
    """Whether to cache the logger configuration and reuse."""

    def configure(self) -> GetLogger:
        """Return logger with the given configuration.

        Returns:
            A 'logging.getLogger' like function.
        """
        try:
            from structlog import configure, get_logger

            # we now configure structlog
            configure(**{k: v for k, v in asdict(self).items() if k != "standard_lib_logging_config"})
            return get_logger
        except ImportError as e:  # pragma: no cover
            raise MissingDependencyException("structlog is not installed") from e
