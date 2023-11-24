from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.constants import SCOPE_STATE_NAMESPACE
from litestar.serialization import get_serializer

from .get import get_litestar_scope_state
from .pop import pop_litestar_scope_state
from .set import set_litestar_scope_state

if TYPE_CHECKING:
    from litestar.types import Scope, Serializer
    from litestar.types.scope import ScopeStateKeyType

__all__ = (
    "delete_litestar_scope_state",
    "get_serializer_from_scope",
    "get_litestar_scope_state",
    "pop_litestar_scope_state",
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


def delete_litestar_scope_state(scope: Scope, key: ScopeStateKeyType) -> None:
    """Delete an internal value from connection scope state.

    Args:
        scope: The connection scope.
        key: Key to set under internal namespace in scope state.
    """
    del scope["state"][SCOPE_STATE_NAMESPACE][key]
