from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, overload

from litestar.constants import SCOPE_STATE_NAMESPACE
from litestar.types.empty import Empty, EmptyType

if TYPE_CHECKING:
    from litestar.datastructures import URL, Accept
    from litestar.types import Scope
    from litestar.types.asgi_types import HTTPResponseBodyEvent, HTTPResponseStartEvent
    from litestar.types.scope import (
        AcceptKey,
        BaseUrlKey,
        BodyKey,
        ContentTypeKey,
        CookiesKey,
        CsrfTokenKey,
        DependencyCacheKey,
        DoCacheKey,
        FormKey,
        HttpResponseBodyKey,
        HttpResponseStartKey,
        IsCachedKey,
        JsonKey,
        MsgpackKey,
        ParsedQueryKey,
        ResponseCompressedKey,
        ScopeStateKeyType,
        UrlKey,
    )

__all__ = ("pop_litestar_scope_state",)

T = TypeVar("T")


@overload
def pop_litestar_scope_state(scope: Scope, key: AcceptKey) -> Accept:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: AcceptKey, default: T) -> Accept | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: BaseUrlKey) -> URL:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: BaseUrlKey, default: T) -> URL | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: BodyKey) -> bytes:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: BodyKey, default: T) -> bytes | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: ContentTypeKey) -> tuple[str, dict[str, str]]:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: ContentTypeKey, default: T) -> tuple[str, dict[str, str]] | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: CookiesKey) -> dict[str, str]:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: CookiesKey, default: T) -> dict[str, str] | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: CsrfTokenKey) -> str:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: CsrfTokenKey, default: T) -> str | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: DependencyCacheKey) -> dict[str, Any]:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: DependencyCacheKey, default: T) -> dict[str, Any] | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: DoCacheKey) -> bool:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: DoCacheKey, default: T) -> bool | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: FormKey) -> dict[str, str | list[str]]:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: FormKey, default: T) -> dict[str, str | list[str]] | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: HttpResponseBodyKey) -> HTTPResponseBodyEvent:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: HttpResponseBodyKey, default: T) -> HTTPResponseBodyEvent | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: HttpResponseStartKey) -> HTTPResponseStartEvent:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: HttpResponseStartKey, default: T) -> HTTPResponseStartEvent | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: IsCachedKey) -> bool:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: IsCachedKey, default: T) -> bool | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: JsonKey) -> Any:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: JsonKey, default: T) -> Any | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: MsgpackKey) -> Any:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: MsgpackKey, default: T) -> Any | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: ParsedQueryKey) -> tuple[tuple[str, str], ...]:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: ParsedQueryKey, default: T) -> tuple[tuple[str, str], ...] | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: ResponseCompressedKey) -> bool:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: ResponseCompressedKey, default: T) -> bool | T:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: UrlKey) -> URL:
    ...


@overload
def pop_litestar_scope_state(scope: Scope, key: UrlKey, default: T) -> URL | T:
    ...


def pop_litestar_scope_state(scope: Scope, key: ScopeStateKeyType, default: T | EmptyType = Empty) -> Any | T:
    """Get an internal value from connection scope state.

    Args:
        scope: The connection scope.
        key: Key to get from internal namespace in scope state.
        default: Default value to return.

    Returns:
        Value mapped to ``key`` in internal connection scope namespace.

    Raises:
        KeyError: If ``key`` is not in internal connection scope namespace and ``default`` is ``Empty``.
    """
    namespace = scope["state"].setdefault(SCOPE_STATE_NAMESPACE, {})
    return namespace.pop(key) if default is Empty else namespace.pop(key, default)
