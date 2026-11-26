from typing import TYPE_CHECKING

from litestar.enums import ScopeType
from litestar.exceptions import MissingDependencyException
from litestar.middleware._utils import build_exclude_path_pattern, should_bypass_middleware
from litestar.middleware.base import ASGIMiddleware

__all__ = ("OpenTelemetryInstrumentationMiddleware",)


try:
    import opentelemetry  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("opentelemetry") from e

from opentelemetry.instrumentation.asgi import OpenTelemetryMiddleware
from opentelemetry.util.http import get_excluded_urls

if TYPE_CHECKING:
    from litestar.plugins.opentelemetry.config import OpenTelemetryConfig
    from litestar.types import ASGIApp, Receive, Scope, Scopes, Send


class OpenTelemetryInstrumentationMiddleware(ASGIMiddleware):
    """OpenTelemetry Middleware."""

    def __init__(self, *, config: "OpenTelemetryConfig") -> None:
        """Middleware that adds OpenTelemetry instrumentation to the application.

        Args:
            config: An instance of
                :class:`OpenTelemetryConfig <litestar.plugins.opentelemetry.OpenTelemetryConfig>`.
        """
        self.config = config
        scope_types: Scopes = set(config.scopes or (ScopeType.HTTP, ScopeType.WEBSOCKET))
        if config.scopes:
            self.scopes = (*(s for s in (ScopeType.HTTP, ScopeType.WEBSOCKET) if s in scope_types), ScopeType.ASGI)
        exclude_path_pattern = build_exclude_path_pattern(exclude=config.exclude or None, middleware_cls=type(self))
        exclude_opt_key = config.exclude_opt_key
        self.should_bypass_for_scope = lambda scope: should_bypass_middleware(
            scope=scope,
            scopes=scope_types,
            exclude_opt_key=exclude_opt_key,
            exclude_path_pattern=exclude_path_pattern,
        )

    def __call__(self, app: "ASGIApp") -> "ASGIApp":
        """Wrap ``app`` in the OpenTelemetry ASGI middleware.

        Args:
            app: The next ASGI application in the middleware stack.

        Returns:
            An ASGI application.
        """
        config = self.config
        instrumented: ASGIApp = OpenTelemetryMiddleware(  # type: ignore[assignment]
            app=app,
            client_request_hook=config.client_request_hook_handler,
            client_response_hook=config.client_response_hook_handler,
            default_span_details=config.scope_span_details_extractor,
            excluded_urls=get_excluded_urls(config.exclude_urls_env_key),
            exclude_spans=config.exclude_spans,
            meter=config.meter,
            meter_provider=config.meter_provider,
            server_request_hook=config.server_request_hook_handler,
            tracer_provider=config.tracer_provider,
            tracer=config.tracer,
            http_capture_headers_server_request=config.http_capture_headers_server_request,
            http_capture_headers_server_response=config.http_capture_headers_server_response,
            http_capture_headers_sanitize_fields=config.http_capture_headers_sanitize_fields,
        )
        handle = self.handle
        should_bypass_for_scope = self.should_bypass_for_scope

        async def middleware(scope: "Scope", receive: "Receive", send: "Send") -> None:
            if should_bypass_for_scope is not None and should_bypass_for_scope(scope):
                await app(scope, receive, send)
            else:
                await handle(scope=scope, receive=receive, send=send, next_app=instrumented)

        return middleware

    async def handle(self, scope: "Scope", receive: "Receive", send: "Send", next_app: "ASGIApp") -> None:
        """Handle ASGI call.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.
            next_app: The next ASGI application in the middleware stack, wrapped in the OpenTelemetry ASGI middleware.
        """
        await next_app(scope, receive, send)
