from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.contrib.opentelemetry.config import OpenTelemetryConfig
from litestar.contrib.opentelemetry.middleware import OpenTelemetryInstrumentationMiddleware
from litestar.middleware.base import DefineMiddleware
from litestar.plugins import InitPluginProtocol

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.types.composite_types import Middleware


class OpenTelemetryPlugin(InitPluginProtocol):
    """OpenTelemetry Plugin."""

    __slots__ = ("_otel_config",)

    def __init__(self, config: OpenTelemetryConfig | None = None) -> None:
        if config is None:
            config = OpenTelemetryConfig()
        self._otel_config = config
        super().__init__()

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.otel = self._otel_config.middleware
        # check if the middleware is passed though the app_config.middlewares this should override the default middleware
        app_config.otel = self._get_otel_middleware(app_config.middleware) or app_config.otel
        return app_config

    @staticmethod
    def _get_otel_middleware(middlewares: list[Middleware]) -> DefineMiddleware | None:
        """Get the OpenTelemetry middleware if it is enabled in the application.
        Remove the middleware from the list of middlewares if it is found.
        """
        for middleware in middlewares:
            if (
                isinstance(middleware, DefineMiddleware)
                and middleware.middleware == OpenTelemetryInstrumentationMiddleware
            ):
                middlewares.remove(middleware)
                return middleware
        return None
