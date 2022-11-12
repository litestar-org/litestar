from typing import TYPE_CHECKING, Dict, Tuple

from starlite.exceptions import MissingDependencyException, NoRouteMatchFoundException

try:
    from opentelemetry.semconv.trace import SpanAttributes
except ImportError as e:
    raise MissingDependencyException("OpenTelemetry dependencies are not installed") from e

if TYPE_CHECKING:
    from starlite.types import Scope


def get_route_details_from_scope(scope: "Scope") -> Tuple[str, Dict[str, str]]:
    """Retrieve the span name and attributes from the ASGI scope.

    Args:
        scope: The ASGI scope instance.

    Returns:
        A tuple includes the span name and attributes dict.
    """
    app, route_handler = scope["app"], scope["route_handler"]
    try:
        span_name = app.route_reverse(route_handler.name or str(route_handler))
        attributes = {SpanAttributes.HTTP_ROUTE: span_name}
    except NoRouteMatchFoundException:
        span_name = f"{str(route_handler)}::{scope.get('method', '')}ֶֶֶ"
        attributes = {}
    return span_name, attributes
