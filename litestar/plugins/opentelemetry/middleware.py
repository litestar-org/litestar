from __future__ import annotations

import copy
import traceback
from typing import TYPE_CHECKING, ClassVar, cast

from litestar.exceptions import MissingDependencyException
from litestar.middleware.base import AbstractMiddleware

__all__ = ("OpenTelemetryInstrumentationMiddleware",)


try:
    import opentelemetry  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("opentelemetry") from e

from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.util.http import get_excluded_urls

if TYPE_CHECKING:
    from opentelemetry.trace import Status  # noqa: F401

    from litestar.plugins.opentelemetry import OpenTelemetryConfig
    from litestar.types import ASGIApp, Receive, Scope, Send


class OpenTelemetryInstrumentationMiddleware(AbstractMiddleware):
    """OpenTelemetry Middleware with enhanced Litestar instrumentation.

    This middleware extends the standard OpenTelemetry ASGI middleware to provide:
    - Exception recording with full stack traces via span.record_exception()
    - Enhanced error status tracking on spans
    """

    __slots__ = ("config", "open_telemetry_middleware")
    __singleton_middleware__: ClassVar[OpenTelemetryMiddleware | None] = None

    def __init__(self, app: ASGIApp, config: OpenTelemetryConfig) -> None:
        """Middleware that adds OpenTelemetry instrumentation to the application.

        Args:
            app: The ``next`` ASGI app to call.
            config: An instance of :class:`OpenTelemetryConfig <.plugins.opentelemetry.OpenTelemetryConfig>`
        """
        super().__init__(app=app, scopes=config.scopes, exclude=config.exclude, exclude_opt_key=config.exclude_opt_key)
        self.config = config

        reuse_singleton = config.tracer_provider is None and self.__class__.__singleton_middleware__ is not None

        if reuse_singleton:
            cloned = cast("OpenTelemetryMiddleware", copy.copy(self.__class__.__singleton_middleware__))
            cloned.app = app
            self.open_telemetry_middleware = cloned
        else:
            self.open_telemetry_middleware = OpenTelemetryMiddleware(
                app=app,
                client_request_hook=config.client_request_hook_handler,  # type: ignore[arg-type]
                client_response_hook=config.client_response_hook_handler,  # type: ignore[arg-type]
                default_span_details=config.scope_span_details_extractor,
                excluded_urls=get_excluded_urls(config.exclude_urls_env_key),
                meter=config.meter,
                meter_provider=config.meter_provider,
                server_request_hook=config.server_request_hook_handler,
                tracer_provider=config.tracer_provider,
            )
            if config.tracer_provider is None:
                self.__class__.__singleton_middleware__ = self.open_telemetry_middleware

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        # Import here to avoid circular dependency and ensure OTEL is optional
        from opentelemetry import trace
        from opentelemetry.trace import Status, StatusCode

        try:
            await self.open_telemetry_middleware(scope, receive, send)  # type: ignore[arg-type] # pyright: ignore[reportGeneralTypeIssues]
        except Exception as exc:
            current_span = trace.get_current_span()
            if current_span.get_span_context().is_valid and current_span.is_recording():
                current_span.record_exception(
                    exc,
                    attributes={
                        "exception.stacktrace": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
                    },
                )
                current_span.set_status(Status(StatusCode.ERROR, str(exc)))
            raise
