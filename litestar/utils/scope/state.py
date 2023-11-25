from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from litestar.constants import CONNECTION_STATE_KEY
from litestar.types import Empty, EmptyType

if TYPE_CHECKING:
    from typing_extensions import Self

    from litestar.datastructures import URL, Accept, Headers
    from litestar.types.asgi_types import Scope


@dataclass
class ConnectionState:
    """An object for storing connection state.

    This is an internal API, and subject to change without notice.

    All types are a union with `EmptyType` and are seeded with the `Empty` value.
    """

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
    log_context: dict[str, Any] = field(default_factory=dict)
    msgpack: Any | EmptyType = Empty
    parsed_query: tuple[tuple[str, str], ...] | EmptyType = Empty
    response_compressed: bool | EmptyType = Empty
    url: URL | EmptyType = Empty

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
