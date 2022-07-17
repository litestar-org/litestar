from typing import TYPE_CHECKING, Any, Dict, Tuple

from opentelemetry.instrumentation.asgi import (
    OpenTelemetryMiddleware as BaseOpenTelemetryMiddleware,
)
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.util.http import get_excluded_urls, parse_excluded_urls
from starlette.routing import Match

from starlite.config import InstrumentationConfig

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Scope

_excluded_urls_from_env = get_excluded_urls("STARLITE")


class OpenTelemetryMiddleware(BaseOpenTelemetryMiddleware):
    """OpenTelemetry middleware for Starlite"""

    def __init__(self, app: "ASGIApp", config: InstrumentationConfig):
        tracer_provider = config.tracer_provider
        server_request_hook = config.server_request_hook
        client_request_hook = config.client_request_hook
        client_response_hook = config.client_response_hook
        excluded_urls = (
            _excluded_urls_from_env if config.excluded_urls is None else parse_excluded_urls(config.excluded_urls)
        )
        super().__init__(
            app=app,
            tracer_provider=tracer_provider,
            excluded_urls=excluded_urls,
            default_span_details=_get_route_details,
            server_request_hook=server_request_hook,
            client_request_hook=client_request_hook,
            client_response_hook=client_response_hook,
        )


def _get_route_details(
    scope: "Scope",
) -> Tuple[Any, Dict]:
    """Callback to retrieve the Starlite route being served.

    TODO: there is currently no way to retrieve http.route from
    a starlette application from scope.  Is there a better way to handle this?

    See: https://github.com/encode/starlette/pull/804
    """
    app = scope["app"]
    route = None
    for starlette_route in app.routes:
        match, _ = starlette_route.matches(scope)
        if match == Match.FULL:
            route = starlette_route.path
            break
        if match == Match.PARTIAL:
            route = starlette_route.path
    # method only exists for http, if websocket
    # leave it blank.
    span_name = route or scope.get("method", "")
    attributes = {}
    if route:
        attributes[SpanAttributes.HTTP_ROUTE] = route
    return span_name, attributes
