from __future__ import annotations

import atexit
import dataclasses
import logging
import logging.config
import os
import queue
import sys
from logging.handlers import QueueListener
from typing import TYPE_CHECKING, Literal, ClassVar, cast, Any

__all__ = ("LoggingConfig",)


if TYPE_CHECKING:
    # these imports are duplicated on purpose so sphinx autodoc can find and link them

    from litestar import Litestar
    from litestar.types import GetLogger, LifespanHook, Logger, Scope
    from litestar.types.callable_types import ExceptionLoggingHandler


if sys.version_info >= (3, 12):
    from logging import getHandlerByName
else:

    def getHandlerByName(name: str) -> logging.Handler:
        return cast(logging.Handler, logging._handlers.get(name))  # type: ignore[attr-defined]


def _default_exception_logging_handler(logger: Logger, scope: Scope, tb: list[str]) -> None:
    logger.exception(
        "Uncaught exception (connection_type=%s, path=%r):",
        scope["type"],
        scope["path"],
    )


class ExtraKeyValueFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        message = super().format(record)

        extras = {
            key.removeprefix("litestar_"): value
            for key, value in record.__dict__.items()
            if key.startswith("litestar_")
        }

        if extras:
            extra_str = " ".join(f"{k}={v}" for k, v in extras.items())
            message = f"{message}: {extra_str}"

        return message


@dataclasses.dataclass(frozen=True)
class LoggingConfig:
    _handler_queue: ClassVar[queue.Queue | None] = None
    _queue_listener: ClassVar[QueueListener | None] = None

    level: Literal[0, 10, 20, 30, 40, 50] = logging.INFO
    """Log level"""
    log_exceptions: Literal["always", "debug", "never"] = "always"
    """When to log exceptions"""
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
    down at interpreter shutdown via an :func:`atexit.atexit` handler. At application
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
    set 'propagate=True' when running under pytest. Useful when working with pytest's 
    'caplog' fixture, as it may not work correctly otherwise
    """

    formatter: type[logging.Formatter] | None = dataclasses.field(default=ExtraKeyValueFormatter)

    supports_json_like_data: bool = False

    @property
    def should_propagate(self) -> bool:
        return self.propagate or (self.always_propagate_on_pytest and "PYTEST_VERSION" in os.environ)

    def configure_logger(self, app: Litestar) -> LifespanHook | None:
        queue_handler_config = {}
        if self.configure_queue_handler:
            if LoggingConfig._handler_queue is None:
                LoggingConfig._handler_queue = queue.Queue(-1)

            queue_handler_config = {
                "litestar_queue_handler": {
                    "()": "logging.handlers.QueueHandler",
                    "queue": LoggingConfig._handler_queue,
                }
            }

        logging.config.dictConfig(
            {
                "version": 1,
                "disable_existing_loggers": False,
                "formatters": {
                    "litestar_formatter": {
                        "format": "%(levelname)s - %(asctime)s - %(name)s - %(module)s - %(message)s",
                    },
                },
                "handlers": {
                    "litestar_stream_handler": {
                        "class": "logging.StreamHandler",
                        "formatter": "litestar_formatter",
                    },
                    **queue_handler_config,
                },
                "loggers": {
                    "litestar": {
                        "handlers": [
                            "litestar_queue_handler" if self.configure_queue_handler else "litestar_stream_handler",
                        ],
                        "level": self.level,
                        "propagate": self.should_propagate,
                    },
                },
            }
        )

        if self.formatter is not None:
            handler = getHandlerByName("litestar_stream_handler")
            handler.setFormatter(self.formatter(handler.formatter._fmt))

        if self.configure_queue_handler:
            if LoggingConfig._queue_listener is None:
                LoggingConfig._queue_listener = QueueListener(
                    LoggingConfig._handler_queue,  # type: ignore[arg-type]
                    getHandlerByName("litestar_stream_handler"),
                )
                atexit.register(LoggingConfig._queue_listener.stop)
            if LoggingConfig._queue_listener._thread is None:
                LoggingConfig._queue_listener.start()

        def shutdown() -> None:
            # if there's a queue, ensure all log records are processed before we allow
            # the app to stop
            if LoggingConfig._handler_queue is not None:
                LoggingConfig._handler_queue.join()

        return shutdown
