from typing import TYPE_CHECKING, Any, Callable, Optional

if TYPE_CHECKING:
    from starlite.types import Scope


def get_serializer_from_scope(scope: "Scope") -> Optional[Callable[[Any], Any]]:
    """
    Utility that returns a serializer given a scope object.
    Args:
        scope: The ASGI connection scope.

    Returns:
        A serializer function
    """

    route_handler = scope["route_handler"]
    if hasattr(route_handler, "resolve_response_class"):
        return route_handler.resolve_response_class().serializer  # type: ignore

    app = scope["app"]
    return app.response_class.serializer if app.response_class else None
