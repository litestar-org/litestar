from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from litestar.logging.structlog import StructLoggingConfig, StructLogLoggingMiddlewareConfig
from litestar.middleware.logging import LoggingMiddlewareConfig
from litestar.plugins import InitPlugin

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


@dataclass
class StructlogConfig:
    structlog_logging_config: StructLoggingConfig = field(default_factory=StructLoggingConfig)
    """Structlog Logging configuration for Litestar.  See ``litestar.logging.config.StructLoggingConfig``` for details."""
    middleware_logging_config: LoggingMiddlewareConfig = field(default_factory=StructLogLoggingMiddlewareConfig)
    """Middleware logging config."""
    enable_middleware_logging: bool = True
    """Enable request logging."""


class StructlogPlugin(InitPlugin):
    """Structlog Plugin."""

    __slots__ = ("_config",)

    def __init__(self, config: StructlogConfig | None = None) -> None:
        if config is None:
            config = StructlogConfig()
        self._config = config
        super().__init__()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        """Structlog Plugin

        Args:
            app_config: The :class:`AppConfig <litestar.config.app.AppConfig>` instance.

        Returns:
            The app config object.
        """
        if isinstance(app_config.logging_config, StructLoggingConfig):
            return app_config

        app_config.logging_config = self._config.structlog_logging_config
        if self._config.enable_middleware_logging:
            app_config.middleware.append(self._config.middleware_logging_config.middleware)
        return app_config
