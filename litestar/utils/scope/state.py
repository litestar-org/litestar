from __future__ import annotations

from typing import TYPE_CHECKING, Any

from msgspec import Struct

from litestar.constants import CONNECTION_STATE_KEY
from litestar.types import Empty, EmptyType
from litestar.utils.empty import value_or_default

if TYPE_CHECKING:
    from typing_extensions import Self

    from litestar.datastructures import URL, Accept, Headers
    from litestar.types.asgi_types import Scope


class ScopeState(Struct):
    accept: Accept | EmptyType = Empty
    base_url: URL | EmptyType = Empty
    body: bytes | EmptyType = Empty
    content_type: tuple[str, dict[str, str]] | EmptyType = Empty
    cookies: dict[str, str] | EmptyType = Empty
    csrf_token: str | EmptyType = Empty
    dependency_cache: dict[str, Any] | EmptyType = Empty
    do_cache: bool | EmptyType = Empty
    form: dict[str, str | list[str]] | EmptyType = Empty
    headers: Headers | EmptyType = Empty
    is_cached: bool | EmptyType = Empty
    json: Any | EmptyType = Empty
    log_context: dict[str, Any] = {}
    msgpack: Any | EmptyType = Empty
    parsed_query: tuple[tuple[str, str], ...] | EmptyType = Empty
    response_compressed: bool | EmptyType = Empty
    url: URL | EmptyType = Empty
    _compat_ns: dict[str, Any] = {}

    @classmethod
    def from_scope(cls, scope: Scope) -> Self:
        """Create a new `ConnectionState` object from a scope.

        Object is cached in the scope's state under the `SCOPE_STATE_NAMESPACE` key.

        Args:
            scope: The ASGI connection scope.

        Returns:
            A `ConnectionState` object.
        """
        if state := scope["state"].get(CONNECTION_STATE_KEY):
            return state  # type: ignore[no-any-return]
        state = scope["state"][CONNECTION_STATE_KEY] = cls()
        scope["state"][CONNECTION_STATE_KEY] = state
        return state


def get_litestar_scope_state(scope: Scope, key: str, default: Any = None, pop: bool = False) -> Any:
    """Get an internal value from connection scope state.

    Args:
        scope: The connection scope.
        key: Key to get from internal namespace in scope state.
        default: Default value to return.
        pop: Boolean flag dictating whether the value should be deleted from the state.

    Returns:
        Value mapped to ``key`` in internal connection scope namespace.
    """
    scope_state = ScopeState.from_scope(scope)
    try:
        return value_or_default(getattr(scope_state, key), default)
    except AttributeError:
        if pop:
            return scope_state._compat_ns.pop(key, default)
        return scope_state._compat_ns.get(key, default)


def set_litestar_scope_state(scope: Scope, key: str, value: Any) -> None:
    """Set an internal value in connection scope state.

    Args:
        scope: The connection scope.
        key: Key to set under internal namespace in scope state.
        value: Value for key.
    """
    scope_state = ScopeState.from_scope(scope)
    if hasattr(scope_state, key):
        setattr(scope_state, key, value)
    else:
        scope_state._compat_ns[key] = value


def delete_litestar_scope_state(scope: Scope, key: str) -> None:
    """Delete an internal value from connection scope state.

    Args:
        scope: The connection scope.
        key: Key to set under internal namespace in scope state.
    """
    scope_state = ScopeState.from_scope(scope)
    if hasattr(scope_state, key):
        setattr(scope_state, key, Empty)
    else:
        del scope_state._compat_ns[key]
