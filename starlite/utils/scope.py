from typing import TYPE_CHECKING, Any, Callable, Optional, cast

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.types import RouteHandlerType, Scope


def get_serializer_from_scope(scope: "Scope") -> Optional[Callable[[Any], Any]]:
    """
    Utility that returns a serializer given a scope object.
    Args:
        scope: The ASGI connection scope.

    Returns:
        A serializer function
    """

    route_handler = cast("RouteHandlerType", scope["route_handler"])
    if hasattr(route_handler, "resolve_response_class"):
        return route_handler.resolve_response_class().serializer  # type: ignore

    app = cast("Starlite", scope["app"])
    return app.response_class.serializer if app.response_class else None
