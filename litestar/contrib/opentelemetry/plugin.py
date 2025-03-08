from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.contrib.opentelemetry.config import OpenTelemetryConfig
from litestar.contrib.opentelemetry.middleware import OpenTelemetryInstrumentationMiddleware
from litestar.plugins import InitPlugin

if TYPE_CHECKING:
    from litestar.config.app import AppConfig


class OpenTelemetryPlugin(InitPlugin):
    """OpenTelemetry Plugin."""

    __slots__ = ("_middleware", "config")

    def __init__(self, config: OpenTelemetryConfig | None = None) -> None:
        self.config = config or OpenTelemetryConfig()
        super().__init__()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.middleware.append(OpenTelemetryInstrumentationMiddleware(self.config))
        return app_config
