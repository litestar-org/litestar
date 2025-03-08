from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.exceptions import MissingDependencyException
from litestar.middleware import ASGIMiddleware

__all__ = ("OpenTelemetryInstrumentationMiddleware",)


try:
    import opentelemetry  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("opentelemetry") from e

from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.util.http import get_excluded_urls

if TYPE_CHECKING:
    from litestar.contrib.opentelemetry import OpenTelemetryConfig
    from litestar.types import ASGIApp, Receive, Scope, Send


class OpenTelemetryInstrumentationMiddleware(ASGIMiddleware):
    """OpenTelemetry Middleware."""

    def __init__(self, config: OpenTelemetryConfig) -> None:
        """Middleware that adds OpenTelemetry instrumentation to the application.

        Args:
            config: An instance of :class:`OpenTelemetryConfig <.contrib.opentelemetry.OpenTelemetryConfig>`
        """
        self.exclude_opt_key = config.exclude_opt_key
        self.exclude_path_pattern = config.exclude
        self.config = config

    async def handle(self, scope: Scope, receive: Receive, send: Send, next_app: ASGIApp) -> None:
        self.open_telemetry_middleware = OpenTelemetryMiddleware(
            app=next_app,
            client_request_hook=self.config.client_request_hook_handler,  # type: ignore[arg-type]
            client_response_hook=self.config.client_response_hook_handler,  # type: ignore[arg-type]
            default_span_details=self.config.scope_span_details_extractor,
            excluded_urls=get_excluded_urls(self.config.exclude_urls_env_key),
            meter=self.config.meter,
            meter_provider=self.config.meter_provider,
            server_request_hook=self.config.server_request_hook_handler,
            tracer_provider=self.config.tracer_provider,
        )
        await self.open_telemetry_middleware(scope, receive, send)  # type: ignore[arg-type] # pyright: ignore[reportGeneralTypeIssues]
