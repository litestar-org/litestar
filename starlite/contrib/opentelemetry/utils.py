from typing import TYPE_CHECKING, Any, Dict, Tuple

from starlite.exceptions import MissingDependencyException

try:
    from opentelemetry.semconv.trace import SpanAttributes
except ImportError as e:
    raise MissingDependencyException("OpenTelemetry dependencies are not installed") from e

if TYPE_CHECKING:
    from starlite.types import Scope


def get_route_details_from_scope(scope: "Scope") -> Tuple[str, Dict[Any, str]]:
    """Retrieve the span name and attributes from the ASGI scope.

    Args:
        scope: The ASGI scope instance.

    Returns:
        A tuple of the span name and a dict of attrs.
    """
    route_handler_fn_name = scope["route_handler"].handler_name
    return route_handler_fn_name, {SpanAttributes.HTTP_ROUTE: route_handler_fn_name}
