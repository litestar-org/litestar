from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.constants import SCOPE_STATE_NAMESPACE
from litestar.serialization import get_serializer

if TYPE_CHECKING:
    from litestar.types import Scope, Serializer

__all__ = (
    "delete_litestar_scope_state",
    "get_serializer_from_scope",
    "get_litestar_scope_state",
    "set_litestar_scope_state",
)


def get_serializer_from_scope(scope: Scope) -> Serializer:
    """Return a serializer given a scope object.

    Args:
        scope: The ASGI connection scope.

    Returns:
        A serializer function
    """
    route_handler = scope["route_handler"]
    app = scope["app"]

    if hasattr(route_handler, "resolve_type_encoders"):
        type_encoders = route_handler.resolve_type_encoders()
    else:
        type_encoders = app.type_encoders or {}

    if response_class := (
        route_handler.resolve_response_class()  # pyright: ignore
        if hasattr(route_handler, "resolve_response_class")
        else app.response_class
    ):
        type_encoders = {**type_encoders, **(response_class.type_encoders or {})}

    return get_serializer(type_encoders)


def get_litestar_scope_state(scope: Scope, key: str, default: Any = None, pop: bool = False) -> Any:
    """Get an internal value from connection scope state.

    Note:
        If called with a default value, this method behaves like to `dict.set_default()`, both setting the key in the
        namespace to the default value, and returning it.

        If called without a default value, the method behaves like `dict.get()`, returning ``None`` if the key does not
        exist.

    Args:
        scope: The connection scope.
        key: Key to get from internal namespace in scope state.
        default: Default value to return.
        pop: Boolean flag dictating whether the value should be deleted from the state.

    Returns:
        Value mapped to ``key`` in internal connection scope namespace.
    """
    namespace = scope["state"].setdefault(SCOPE_STATE_NAMESPACE, {})
    return namespace.pop(key, default) if pop else namespace.get(key, default)


def set_litestar_scope_state(scope: Scope, key: str, value: Any) -> None:
    """Set an internal value in connection scope state.

    Args:
        scope: The connection scope.
        key: Key to set under internal namespace in scope state.
        value: Value for key.
    """
    scope["state"].setdefault(SCOPE_STATE_NAMESPACE, {})[key] = value


def delete_litestar_scope_state(scope: Scope, key: str) -> None:
    """Delete an internal value from connection scope state.

    Args:
        scope: The connection scope.
        key: Key to set under internal namespace in scope state.
    """
    del scope["state"][SCOPE_STATE_NAMESPACE][key]
