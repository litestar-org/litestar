from __future__ import annotations

import dataclasses
import functools
import logging
import sys
from typing import TYPE_CHECKING, Any, Callable

import structlog

from litestar.logging.config import LoggingConfig
from litestar.serialization.msgspec_hooks import _msgspec_json_encoder
from litestar.types.callable_types import ExceptionLoggingHandler

if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar import Litestar
    from litestar.types import LifespanHook, Scope, GetLogger, Logger


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


def stdlib_extra_processor(
    logger: logging.Logger,
    method_name: str,
    event_dict: structlog.typing.EventDict,
):
    if "extra" in event_dict:
        extras = {
            key.removeprefix("litestar_"): value
            for key, value in event_dict.pop("extra").items()
            if key.startswith("litestar_")
        }
        event_dict.update(extras)

    return event_dict


LITESTAR_PROCESSORS = (stdlib_extra_processor,)


@dataclasses.dataclass(frozen=True)
class StructLoggingConfig(LoggingConfig):
    exception_logging_handler: ExceptionLoggingHandler = dataclasses.field(default=structlog_exception_logging_handler)  # type: ignore[assignment]
    formatter: logging.Formatter = dataclasses.field(default=None)
    """
    This should always be 'None' to disable the Litestar formatter for structlog
    """
    can_log_structured_data: bool = dataclasses.field(default=True)

    pretty_print_tty: bool = True
    """Pretty print log output when run from an interactive terminal."""

    processors: Iterable[structlog.typing.Processor] | None = None
    """
    Passed to :class:`structlog.typing.BindableLogger`
    """

    wrapper_class: type[structlog.typing.BindableLogger] | None = None
    """
    Passed to :class:`structlog.typing.BindableLogger`
    """

    context_class: type[structlog.typing.Context] | None = None
    """
    Passed to :class:`structlog.typing.BindableLogger`
    """

    logger_factory: Callable[..., structlog.typing.WrappedLogger] | None = None
    """
    Passed to :func:`structlog.configure` It is highly recommended to use 
    :class:`structlog.stdlib.LoggerFactory`, as it will use the 
    ``litestar_queue_handler`` to ensure non-blocking logging
    """

    cache_logger_on_first_use: bool = True
    """
    Passed to :class:`structlog.typing.BindableLogger`
    """

    _structlog_config: dict[str, Any] | None = None

    @property
    def should_log_as_json(self) -> bool:
        if sys.stderr.isatty():
            return not self.pretty_print_tty
        return True

    def __post_init__(self) -> None:
        processors = self.processors
        if processors is None:
            if self.should_log_as_json:
                processors = json_processors()
            else:
                processors = structlog.get_config()["processors"]

        wrapper_class = structlog.make_filtering_bound_logger(self.level)
        if self.wrapper_class is not None:
            wrapper_class = type(
                f"{wrapper_class.__name__}_{self.wrapper_class.__name__}", (wrapper_class, self.wrapper_class), {}
            )

        config = {
            "processors": [*LITESTAR_PROCESSORS, *processors],
            "wrapper_class": wrapper_class,
            "context_class": self.context_class,
            "cache_logger_on_first_use": self.cache_logger_on_first_use,
        }
        # get around frozen dataclasses
        object.__setattr__(self, "_structlog_config", config)

    def get_litestar_logger(self, name: str | None = None) -> Logger:
        return structlog.wrap_logger(
            super().get_litestar_logger(name) if self.logger_factory is None else self.logger_factory(name),
            **self._structlog_config,
        )
