from __future__ import annotations

import atexit
import dataclasses
import logging
import logging.config
import os
import queue
import sys
from logging.handlers import QueueListener
from typing import TYPE_CHECKING, Any, ClassVar, Literal, cast

__all__ = (
    "ExtraKeyValueFormatter",
    "LoggingConfig",
)

from litestar.plugins import InitPlugin

if TYPE_CHECKING:
    # these imports are duplicated on purpose so sphinx autodoc can find and link them

    from litestar.config.app import AppConfig
    from litestar.types import GetLogger, LifespanHook, Logger, Scope
    from litestar.types.callable_types import ExceptionLoggingHandler


if sys.version_info >= (3, 12):
    from logging import getHandlerByName
else:

    def getHandlerByName(name: str) -> logging.Handler:  # noqa: N802
        return cast("logging.Handler", logging._handlers.get(name))  # type: ignore[attr-defined]


def _default_exception_logging_handler(logger: Logger, scope: Scope, tb: list[str]) -> None:
    logger.exception(
        "Uncaught exception (connection_type=%s, path=%r):",
        scope["type"],
        scope["path"],
    )


class ExtraKeyValueFormatter(logging.Formatter):
    """Formatter that extracts items from a 'LogRecord.extra' ``litestar`` key"""

    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        extras: dict[str, Any] | None = getattr(record, "litestar", None)

        if extras:
            extra_str = ", ".join(f"{k}={v}" for k, v in extras.items())
            message = f"{message}: {extra_str}"

        return message


@dataclasses.dataclass(frozen=True)
class LoggingConfig(InitPlugin):
    _handler_queue: ClassVar[queue.Queue | None] = None
    _queue_listener: ClassVar[QueueListener | None] = None

    root_logger_name: str = "litestar"
    """Name of the litestar root logger"""

    level: Literal[0, 10, 20, 30, 40, 50] = logging.INFO
    """Log level"""

    log_exceptions: Literal["always", "debug", "never"] = "always"
    """When to log exceptions"""

    log_requests: bool = False
    """
    Log details about requests.

    This is a convenience function and functionally equivalent to passing
    :class:`~litestar.middleware.logging.LoggingMiddleware` to the root Litestar app.
    To configure request logging more precisely, set ``log_requests=False``, and pass
    the middleware manually.
    """

    disable_stack_trace: set[int | type[Exception]] = dataclasses.field(default_factory=set)
    """Set of http status codes and exceptions to disable stack trace logging for."""

    exception_logging_handler: ExceptionLoggingHandler = _default_exception_logging_handler
    """Handler function for logging exceptions."""

    get_logger: GetLogger = logging.getLogger
    """
    :func:`logging.getLogger`-like function to retrieve a logger. Litestar will use this
    to create its own loggers, so it can be used to provide a custom logger
    """

    configure_queue_handler: bool = True
    """
    Set up a :class:`logging.handlers.QueueHandler`, to ensure logging does not block
    async execution on the main thread. The handler will be registered as
    ``litestar_queue_handler``. This handler will be created *once*, globally, and shut
    down at interpreter shutdown via an :func:`atexit.register` handler. At application
    shutdown, the handler queue will be :meth:`joined <queue.Queue.join>`, to ensure all
    messages are processed properly.

    This should be set to ``True`` unless a different method of asynchronous log
    handling is provided for the litestar logger
    """

    propagate: bool = False
    """
    Propagate logs to higher order handlers
    """

    always_propagate_on_pytest: bool = True
    """
    Set 'propagate=True' when running under pytest. Useful when working with pytest's
    'caplog' fixture, as it may not work correctly otherwise
    """

    disable: bool = False
    """
    Disable all Litestar loggers. This will register a :class:`logging.NullHandler` for
    the litestar loggers.
    """

    formatter: type[logging.Formatter] | None = dataclasses.field(default=ExtraKeyValueFormatter)
    """
    Logging formatter to use for the Litestar logger.
    """

    can_log_structured_data: bool = False
    """
    Whether the logger supports structured data, e.g. 'dict' or 'list'.
    """

    @property
    def should_propagate(self) -> bool:
        return self.propagate or (self.always_propagate_on_pytest and "PYTEST_VERSION" in os.environ)

    def get_litestar_logger(self, name: str | None = None) -> Logger:
        """Get a litestar logger. If 'name' is given and not the name of the root logger,
        a child logger of the root logger will be returned, e.g. requesting 'stores'
        will return a logger named 'litestar.stores'.
        """
        logger = self.get_logger(self.root_logger_name)
        if name and name != self.root_logger_name:
            logger = logger.getChild(name)  # type: ignore[attr-defined]
        return logger

    def _configure_logger(self) -> LifespanHook | None:
        """Configure the Litestar logger. Should only be called once per application.

        Optionally returns a 'LifespanHook' that will be called on application
        shutdown.
        """
        handler_name = "litestar_default_handler"

        if self.disable:
            handlers = {
                "litestar_default_handler": {
                    "class": "logging.NullHandler",
                }
            }
        elif self.configure_queue_handler:
            if LoggingConfig._handler_queue is None:
                LoggingConfig._handler_queue = queue.Queue(-1)

            handlers = {
                "litestar_default_handler": {
                    "class": "logging.StreamHandler",
                    "formatter": "litestar_formatter",
                },
                "litestar_queue_handler": {
                    "()": "logging.handlers.QueueHandler",
                    "queue": LoggingConfig._handler_queue,
                },
            }
            handler_name = "litestar_queue_handler"
        else:
            handlers = {
                "litestar_default_handler": {
                    "class": "logging.StreamHandler",
                    "formatter": "litestar_formatter",
                },
            }

        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "litestar_formatter": {
                        "format": "%(levelname)s - %(asctime)s - %(name)s - %(message)s",
                    },
                },
                "handlers": handlers,
                "loggers": {
                    self.root_logger_name: {
                        "handlers": [handler_name],
                        "level": self.level,
                        "propagate": self.should_propagate,
                    },
                },
            }
        )

        if self.formatter is not None:
            handler = getHandlerByName("litestar_default_handler")
            if handler.formatter:
                handler.setFormatter(self.formatter(handler.formatter._fmt))  # type: ignore[union-attr]

        if not self.disable and self.configure_queue_handler:
            if LoggingConfig._queue_listener is None:
                LoggingConfig._queue_listener = QueueListener(
                    LoggingConfig._handler_queue,  # type: ignore[arg-type]
                    getHandlerByName("litestar_default_handler"),
                )
                atexit.register(LoggingConfig._queue_listener.stop)
            if LoggingConfig._queue_listener._thread is None:
                LoggingConfig._queue_listener.start()

    @staticmethod
    def _shutdown() -> None:
        # if there's a queue, ensure all log records are processed before we allow
        # the app to stop
        if LoggingConfig._handler_queue is not None:
            LoggingConfig._handler_queue.join()

    def _get_plugin(self) -> LoggingPlugin:
        return LoggingPlugin(self)


class LoggingPlugin(InitPlugin):
    def __init__(self, config: LoggingConfig) -> None:
        self.config = config

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        self.config._configure_logger()
        if self.config.log_requests:
            from litestar.middleware.logging import LoggingMiddleware

            app_config.middleware.append(LoggingMiddleware())

        app_config.on_shutdown.append(self.config._shutdown)

        return app_config
