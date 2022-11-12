from typing import TYPE_CHECKING

from starlite.exceptions import MissingDependencyException
from starlite.middleware.base import AbstractMiddleware

try:
    from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
except ImportError as e:
    raise MissingDependencyException("OpenTelemetry dependencies are not installed") from e

if TYPE_CHECKING:
    from starlite.contrib.open_telemetry import OpenTelemetryConfig
    from starlite.types import ASGIApp, Receive, Scope, Send


class OpenTelemetryInstrumentationMiddleware(AbstractMiddleware):
    """OpenTelemetry Middleware."""

    __slots__ = ("open_telemetry_middleware",)

    def __init__(self, app: "ASGIApp", config: "OpenTelemetryConfig"):
        """Middleware that adds OpenTelemetry instrumentation to the application.

        Args:
            app: The 'next' ASGI app to call.
            config: An instance of [OpenTelemetryConfig][starlite.contrib.open_telemetry.OpenTelemetryConfig]
        """
        super().__init__(app=app, scopes=config.scopes, exclude=config.exclude, exclude_opt_key=config.exclude_opt_key)
        self.open_telemetry_middleware = OpenTelemetryMiddleware(
            app=app,
            default_span_details=config.scope_span_details_extractor,
            server_request_hook=config.server_request_hook_handler,
            client_request_hook=config.client_request_hook_handler,
            client_response_hook=config.client_response_hook_handler,
            tracer_provider=config.tracer_provider,
            meter_provider=config.meter_provider,
            meter=config.meter_provider,
        )

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """ASGI callable.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        await self.open_telemetry_middleware(scope, receive, send)
