from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from importlib.util import find_spec
from logging import INFO
from typing import TYPE_CHECKING, Any, Callable, Literal, cast

from litestar.exceptions import ImproperlyConfiguredException, MissingDependencyException
from litestar.serialization import encode_json

__all__ = ("BaseLoggingConfig", "LoggingConfig", "StructLoggingConfig")


if TYPE_CHECKING:
    from typing import NoReturn

    # these imports are duplicated on purpose so sphinx autodoc can find and link them
    from structlog.types import BindableLogger, Processor, WrappedLogger

    from litestar.types import Logger, Scope
    from litestar.types.callable_types import ExceptionLoggingHandler, GetLogger


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
        "class": "litestar.logging.standard.QueueListenerHandler",
        "level": "DEBUG",
        "formatter": "standard",
    },
}

if sys.version_info >= (3, 12, 0):
    default_handlers["queue_listener"]["handlers"] = ["console"]


default_picologging_handlers: dict[str, dict[str, Any]] = {
    "console": {
        "class": "picologging.StreamHandler",
        "level": "DEBUG",
        "formatter": "standard",
    },
    "queue_listener": {
        "class": "litestar.logging.picologging.QueueListenerHandler",
        "level": "DEBUG",
        "formatter": "standard",
    },
}


def get_logger_placeholder(_: str | None = None) -> NoReturn:
    """Raise: An :class:`ImproperlyConfiguredException <.exceptions.ImproperlyConfiguredException>`"""
    raise ImproperlyConfiguredException(
        "cannot call '.get_logger' without passing 'logging_config' to the Litestar constructor first"
    )


def _get_default_handlers() -> dict[str, dict[str, Any]]:
    """Return the default logging handlers for the config.

    Returns:
        A dictionary of logging handlers
    """
    if find_spec("picologging"):
        return default_picologging_handlers
    return default_handlers


def _default_exception_logging_handler_factory(
    is_struct_logger: bool, traceback_line_limit: int
) -> ExceptionLoggingHandler:
    """Create an exception logging handler function.

    Args:
        is_struct_logger: Whether the logger is a structlog instance.
        traceback_line_limit: Maximal number of lines to log from the
            traceback.

    Returns:
        An exception logging handler.
    """

    def _default_exception_logging_handler(logger: Logger, scope: Scope, tb: list[str]) -> None:
        # we limit the length of the stack trace to 20 lines.
        first_line = tb.pop(0)

        if is_struct_logger:
            logger.exception(
                "uncaught exception",
                connection_type=scope["type"],
                path=scope["path"],
                traceback="".join(tb[-traceback_line_limit:]),
            )
        else:
            stack_trace = first_line + "".join(tb[-traceback_line_limit:])
            logger.exception(
                "exception raised on %s connection to route %s\n\n%s", scope["type"], scope["path"], stack_trace
            )

    return _default_exception_logging_handler


class BaseLoggingConfig(ABC):
    """Abstract class that should be extended by logging configs."""

    __slots__ = ("log_exceptions", "traceback_line_limit", "exception_logging_handler")

    log_exceptions: Literal["always", "debug", "never"]
    """Should exceptions be logged, defaults to log exceptions when ``app.debug == True``'"""
    traceback_line_limit: int
    """Max number of lines to print for exception traceback"""
    exception_logging_handler: ExceptionLoggingHandler | None
    """Handler function for logging exceptions."""

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
    handlers: dict[str, dict[str, Any]] = field(default_factory=_get_default_handlers)
    """A dict in which each key is a handler id and each value is a dict describing how to configure the corresponding
    Handler instance.
    """
    loggers: dict[str, dict[str, Any]] = field(
        default_factory=lambda: {
            "litestar": {"level": "INFO", "handlers": ["queue_listener"], "propagate": False},
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
    log_exceptions: Literal["always", "debug", "never"] = field(default="debug")
    """Should exceptions be logged, defaults to log exceptions when 'app.debug == True'"""
    traceback_line_limit: int = field(default=20)
    """Max number of lines to print for exception traceback"""
    exception_logging_handler: ExceptionLoggingHandler | None = field(default=None)
    """Handler function for logging exceptions."""

    def __post_init__(self) -> None:
        if "queue_listener" not in self.handlers:
            self.handlers["queue_listener"] = _get_default_handlers()["queue_listener"]

        if "litestar" not in self.loggers:
            self.loggers["litestar"] = {
                "level": "INFO",
                "handlers": ["queue_listener"],
                "propagate": False,
            }

        if self.log_exceptions != "never" and self.exception_logging_handler is None:
            self.exception_logging_handler = _default_exception_logging_handler_factory(
                is_struct_logger=False, traceback_line_limit=self.traceback_line_limit
            )

    def configure(self) -> GetLogger:
        """Return logger with the given configuration.

        Returns:
            A 'logging.getLogger' like function.
        """

        if "picologging" in str(encode_json(self.handlers)):
            try:
                import picologging  # noqa: F401
            except ImportError as e:
                raise MissingDependencyException("picologging") from e

            from picologging import config, getLogger

            values = {k: v for k, v in asdict(self).items() if v is not None and k != "incremental"}
        else:
            from logging import config, getLogger  # type: ignore[no-redef, assignment]

            values = {k: v for k, v in asdict(self).items() if v is not None}

        config.dictConfig(values)
        return cast("Callable[[str], Logger]", getLogger)


def default_json_serializer(value: Any, default: Callable[[Any], Any] | None = None) -> bytes:
    return encode_json(value=value, serializer=default)


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
            structlog.processors.JSONRenderer(serializer=default_json_serializer),
        ]
    except ImportError:
        return None


def default_wrapper_class() -> type[BindableLogger] | None:  # pyright: ignore
    """Set the default wrapper class for structlog.

    Returns:
        An optional wrapper class.
    """

    try:
        import structlog

        return structlog.make_filtering_bound_logger(INFO)
    except ImportError:
        return None


def default_logger_factory() -> Callable[..., WrappedLogger] | None:
    """Set the default logger factory for structlog.

    Returns:
        An optional logger factory.
    """
    try:
        import structlog

        return structlog.BytesLoggerFactory()
    except ImportError:
        return None


@dataclass
class StructLoggingConfig(BaseLoggingConfig):
    """Configuration class for structlog.

    Notes:
        - requires ``structlog`` to be installed.
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
    log_exceptions: Literal["always", "debug", "never"] = field(default="debug")
    """Should exceptions be logged, defaults to log exceptions when 'app.debug == True'"""
    traceback_line_limit: int = field(default=20)
    """Max number of lines to print for exception traceback"""
    exception_logging_handler: ExceptionLoggingHandler | None = field(default=None)
    """Handler function for logging exceptions."""

    def __post_init__(self) -> None:
        if self.log_exceptions != "never" and self.exception_logging_handler is None:
            self.exception_logging_handler = _default_exception_logging_handler_factory(
                is_struct_logger=True, traceback_line_limit=self.traceback_line_limit
            )

    def configure(self) -> GetLogger:
        """Return logger with the given configuration.

        Returns:
            A 'logging.getLogger' like function.
        """
        try:
            import structlog  # noqa: F401
        except ImportError as e:
            raise MissingDependencyException("structlog") from e

        from structlog import configure, get_logger

        configure(
            **{
                k: v
                for k, v in asdict(self).items()
                if k
                not in (
                    "standard_lib_logging_config",
                    "log_exceptions",
                    "traceback_line_limit",
                    "exception_logging_handler",
                )
            }
        )
        return get_logger
