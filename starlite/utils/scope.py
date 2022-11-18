from typing import TYPE_CHECKING, Any, Optional

from starlite.constants import STARLITE

if TYPE_CHECKING:
    from starlite.types import Scope, Serializer


def get_serializer_from_scope(scope: "Scope") -> Optional["Serializer"]:
    """Return a serializer given a scope object.

    Args:
        scope: The ASGI connection scope.

    Returns:
        A serializer function
    """
    route_handler = scope["route_handler"]
    if hasattr(route_handler, "resolve_response_class"):
        return route_handler.resolve_response_class().serializer  # pyright: ignore

    app = scope["app"]
    return app.response_class.serializer if app.response_class else None


def get_starlite_scope_state(scope: "Scope", key: str, default: Any = None) -> Any:
    """Get an internal value from connection scope state.

    Args:
        scope: The connection scope.
        key: Key to set under internal namespace in scope state.
        default: Value set in internal namespace and returned if `key` doesn't exist.

    Returns:
        Value mapped to `key` in internal connection scope namespace. Returns `None` if `key` not in internal namespace.
    """
    return scope["state"].setdefault(STARLITE, {}).setdefault(key, default)


def set_starlite_scope_state(scope: "Scope", key: str, value: Any) -> None:
    """Set an internal value in connection scope state.

    Args:
        scope: The connection scope.
        key: Key to set under internal namespace in scope state.
        value: Value for key.
    """
    scope["state"].setdefault(STARLITE, {})[key] = value
