from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.contrib.opentelemetry.config import OpenTelemetryConfig
from litestar.contrib.opentelemetry.middleware import OpenTelemetryInstrumentationMiddleware
from litestar.middleware.base import DefineMiddleware
from litestar.plugins import InitPlugin

if TYPE_CHECKING:
    from litestar.config.app import AppConfig
    from litestar.types.composite_types import Middleware


class OpenTelemetryPlugin(InitPlugin):
    """OpenTelemetry Plugin."""

    __slots__ = ("_middleware", "config")

    def __init__(self, config: OpenTelemetryConfig | None = None) -> None:
        self.config = config or OpenTelemetryConfig()
        self._middleware: DefineMiddleware | None = None
        super().__init__()

    @property
    def middleware(self) -> DefineMiddleware:
        if self._middleware:
            return self._middleware
        return DefineMiddleware(OpenTelemetryInstrumentationMiddleware, config=self.config)

    def on_app_init(self, app_config: AppConfig) -> AppConfig:
        app_config.middleware, _middleware = self._pop_otel_middleware(app_config.middleware)
        return app_config

    @staticmethod
    def _pop_otel_middleware(middlewares: list[Middleware]) -> tuple[list[Middleware], DefineMiddleware | None]:
        """Get the OpenTelemetry middleware if it is enabled in the application.
        Remove the middleware from the list of middlewares if it is found.
        """
        otel_middleware: DefineMiddleware | None = None
        other_middlewares = []
        for middleware in middlewares:
            if (
                isinstance(middleware, DefineMiddleware)
                and isinstance(middleware.middleware, type)
                and issubclass(middleware.middleware, OpenTelemetryInstrumentationMiddleware)
            ):
                otel_middleware = middleware
            else:
                other_middlewares.append(middleware)
        return other_middlewares, otel_middleware
