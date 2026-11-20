from typing import TYPE_CHECKING, Any

from litestar.exceptions import MissingDependencyException

__all__ = ("get_route_details_from_scope",)


try:
    import opentelemetry  # noqa: F401
except ImportError as e:
    raise MissingDependencyException("opentelemetry") from e

from opentelemetry.semconv.attributes.http_attributes import HTTP_ROUTE
from opentelemetry.util.http import sanitize_method

if TYPE_CHECKING:
    from litestar.types import Scope


def get_route_details_from_scope(scope: "Scope") -> "tuple[str, dict[Any, str]]":
    """Retrieve the span name and attributes from the ASGI scope.

    Args:
        scope: The ASGI scope instance.

    Returns:
        A tuple of the span name and a dict of attrs.
    """

    if method := str(scope.get("method", "")).strip():
        method = sanitize_method(method)
        if method == "_OTHER":
            method = "HTTP"

    if not (path_template := scope.get("path_template")):
        return method or "websocket", {}

    return (f"{method} {path_template}" if method else path_template), {HTTP_ROUTE: path_template}
