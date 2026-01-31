from __future__ import annotations

import dataclasses
import sys
from typing import TYPE_CHECKING, Any, Callable

import structlog

from litestar.logging.config import LoggingConfig
from litestar.middleware.logging import StructLoggingMiddleware, LoggingMiddleware
from litestar.serialization.msgspec_hooks import _msgspec_json_encoder
from litestar.types.callable_types import ExceptionLoggingHandler

if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar import Litestar
    from litestar.types import LifespanHook, Scope, GetLogger


def structlog_exception_logging_handler(logger: structlog.BoundLogger, scope: Scope, tb: list[str]) -> None:
    logger.exception(
        "Uncaught exception",
        connection_type=scope["type"],
        path=scope["path"],
    )


def json_serializer(value: structlog.typing.EventDict, **_: Any) -> str:
    return _msgspec_json_encoder.encode(value).decode()


def json_processors() -> list[structlog.typing.Processor]:
    return [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.format_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.JSONRenderer(serializer=json_serializer),
    ]


@dataclasses.dataclass(frozen=True)
class StructLoggingConfig(LoggingConfig):
    get_logger: GetLogger = structlog.get_logger
    exception_logging_handler: ExceptionLoggingHandler = dataclasses.field(default=structlog_exception_logging_handler)  # type: ignore[assignment]

    configure_structlog: bool = True
    """
    Whether to call :func:`structlog.configure`
    """

    pretty_print_tty: bool = True
    """Pretty print log output when run from an interactive terminal."""

    processors: Iterable[structlog.typing.Processor] | None = None
    """
    Passed to :func:`structlog.configure`
    """
    wrapper_class: type[structlog.typing.BindableLogger] | None = None
    """
    Passed to :func:`structlog.configure`
    """
    context_class: type[structlog.typing.Context] | None = None
    """
    Passed to :func:`structlog.configure`
    """
    logger_factory: Callable[..., structlog.typing.WrappedLogger] | None = structlog.stdlib.LoggerFactory
    """
    Passed to :func:`structlog.configure` It is highly recommended to use 
    :class:`structlog.stdlib.LoggerFactory`, as it will use the 
    ``litestar_queue_handler`` to ensure non-blocking logging
    """
    cache_logger_on_first_use: bool | None = True
    """
    Passed to :func:`structlog.configure`
    """

    @property
    def should_log_as_json(self) -> bool:
        if sys.stderr.isatty():
            return not self.pretty_print_tty
        return True

    def configure_logger(self, app: Litestar) -> LifespanHook | None:
        if self.configure_structlog:
            processors = self.processors
            if processors is None and self.should_log_as_json:
                processors = json_processors()

            wrapper_class = structlog.make_filtering_bound_logger(self.level)
            if self.wrapper_class is not None:
                wrapper_class = type(
                    f"{wrapper_class.__name__}_{self.wrapper_class.__name__}", (wrapper_class, self.wrapper_class), {}
                )

            structlog.configure(
                processors=processors,
                wrapper_class=wrapper_class,
                context_class=self.context_class,
                logger_factory=self.logger_factory() if self.logger_factory else None,
                cache_logger_on_first_use=self.cache_logger_on_first_use,
            )

        return super().configure_logger(app=app)
