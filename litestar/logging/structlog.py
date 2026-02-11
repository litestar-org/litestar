from __future__ import annotations

import dataclasses
import sys
from typing import TYPE_CHECKING, Any, Callable, cast

import structlog

from litestar.logging.config import LoggingConfig
from litestar.serialization.msgspec_hooks import _msgspec_json_encoder
from litestar.types import Empty, EmptyType, Logger, Scope

if TYPE_CHECKING:
    import logging
    from collections.abc import Iterable

    from litestar.types.callable_types import ExceptionLoggingHandler


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
) -> structlog.typing.EventDict:
    if "extra" in event_dict:
        extra = event_dict.pop("extra")
        if isinstance(extra, dict):
            event_dict.update(extra.pop("litestar", {}))

    return event_dict


LITESTAR_PROCESSORS = (stdlib_extra_processor,)


@dataclasses.dataclass(frozen=True)
class StructLoggingConfig(LoggingConfig):
    exception_logging_handler: ExceptionLoggingHandler = dataclasses.field(default=structlog_exception_logging_handler)  # type: ignore[assignment]
    formatter: type[logging.Formatter] | None = dataclasses.field(default=None)
    """
    This should always be 'None' to disable the Litestar formatter for structlog
    """
    can_log_structured_data: bool = dataclasses.field(default=True)

    pretty_print_tty: bool = True
    """Pretty print log output when run from an interactive terminal."""

    processors: Iterable[structlog.typing.Processor] | None | EmptyType = Empty
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

    bypass_processors_under_capture_logs: bool = True
    """
    Disable all processors when running 'capture_logs()' is active
    """

    _structlog_config: dict[str, Any] | None = None

    @property
    def should_log_as_json(self) -> bool:
        if sys.stderr.isatty():
            return not self.pretty_print_tty
        return True

    def _get_structlog_config(self) -> dict[str, None]:
        if self._structlog_config is None:
            if (
                self.bypass_processors_under_capture_logs
                and (config_processors := structlog.get_config()["processors"])
                and len(config_processors) == 1
                and isinstance(config_processors[0], structlog.testing.LogCapture)
            ):
                config_processors.insert(0, stdlib_extra_processor)
                processors = None
            else:
                processors = self.processors
                if processors is Empty:
                    if self.should_log_as_json:
                        processors = json_processors()
                    else:
                        processors = structlog.get_config()["processors"]
                if processors:
                    processors = [*LITESTAR_PROCESSORS, *processors]

            wrapper_class = structlog.make_filtering_bound_logger(self.level)
            if self.wrapper_class is not None:
                wrapper_class = type(
                    f"{wrapper_class.__name__}_{self.wrapper_class.__name__}", (wrapper_class, self.wrapper_class), {}
                )

            config = {
                "processors": processors,
                "wrapper_class": wrapper_class,
                "context_class": self.context_class,
                "cache_logger_on_first_use": self.cache_logger_on_first_use,
            }
            # get around frozen dataclasses
            object.__setattr__(self, "_structlog_config", config)

        return self._structlog_config

    def get_litestar_logger(self, name: str | None = None) -> Logger:
        logger = structlog.wrap_logger(
            super().get_litestar_logger(name) if self.logger_factory is None else self.logger_factory(name),
            **(self._get_structlog_config() or {}),
        )
        return cast("Logger", logger)
