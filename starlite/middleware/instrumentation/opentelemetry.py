from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union

from opentelemetry.instrumentation.asgi import (
    OpenTelemetryMiddleware as BaseOpenTelemetryMiddleware,
)
from opentelemetry.semconv.trace import SpanAttributes
from opentelemetry.util.http import get_excluded_urls, parse_excluded_urls
from starlette.routing import Match

if TYPE_CHECKING:
    from opentelemetry.instrumentation.asgi import (
        _ClientRequestHookT,
        _ClientResponseHookT,
        _ServerRequestHookT,
    )
    from opentelemetry.util.http import ExcludeList
    from starlette.types import ASGIApp, Scope

_excluded_urls_from_env = get_excluded_urls("STARLITE")


class OpenTelemetryMiddleware(BaseOpenTelemetryMiddleware):  # type: ignore
    """OpenTelemetry middleware for Starlite"""

    def __init__(
        self,
        app: "ASGIApp",
        excluded_urls: Optional[Union[str, "ExcludeList"]] = None,
        server_request_hook: "_ServerRequestHookT" = None,
        client_request_hook: "_ClientRequestHookT" = None,
        client_response_hook: "_ClientResponseHookT" = None,
        tracer_provider: Optional[str] = None,
    ):
        if excluded_urls is None:
            excluded_urls = _excluded_urls_from_env
        elif isinstance(excluded_urls, str):
            excluded_urls = parse_excluded_urls(excluded_urls)
        super().__init__(
            app,
            excluded_urls=excluded_urls,
            server_request_hook=server_request_hook,
            client_request_hook=client_request_hook,
            client_response_hook=client_response_hook,
            tracer_provider=tracer_provider,
            default_span_details=_get_route_details,
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
