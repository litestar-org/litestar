from typing import TYPE_CHECKING, Any, Optional

from starlite.constants import SCOPE_STATE_NAMESPACE
from starlite.types import Empty

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
    app = scope["app"]

    if response_class := (
        route_handler.resolve_response_class()  # pyright: ignore
        if hasattr(route_handler, "resolve_response_class")
        else app.response_class
    ):
        return response_class.get_serializer(
            route_handler.resolve_type_encoders()  # pyright: ignore
            if hasattr(route_handler, "resolve_type_encoders")
            else app.type_encoders
        )

    return None


def get_starlite_scope_state(scope: "Scope", key: str, default: Any = Empty) -> Any:
    """Get an internal value from connection scope state.

    Note:
        If called with a default value, this method behaves like to `dict.set_default()`, both setting the key in the
        namespace to the default value, and returning it.

        If called without a default value, the method behaves like `dict.get()`, returning `None` if the key does not
        exist.

    Args:
        scope: The connection scope.
        key: Key to get from internal namespace in scope state.
        default: Value set in internal namespace and returned if `key` doesn't exist.

    Returns:
        Value mapped to `key` in internal connection scope namespace.
    """
    namespace = scope["state"].setdefault(SCOPE_STATE_NAMESPACE, {})
    if default is Empty:
        return namespace.get(key)
    return namespace.setdefault(key, default)


def set_starlite_scope_state(scope: "Scope", key: str, value: Any) -> None:
    """Set an internal value in connection scope state.

    Args:
        scope: The connection scope.
        key: Key to set under internal namespace in scope state.
        value: Value for key.
    """
    scope["state"].setdefault(SCOPE_STATE_NAMESPACE, {})[key] = value
