from __future__ import annotations

from typing import TYPE_CHECKING, Any, TypeVar, overload

from litestar.constants import SCOPE_STATE_NAMESPACE

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

__all__ = ("get_litestar_scope_state",)

T = TypeVar("T")


@overload
def get_litestar_scope_state(scope: Scope, key: AcceptKey) -> Accept | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: AcceptKey, default: T) -> Accept | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: BaseUrlKey) -> URL | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: BaseUrlKey, default: T) -> URL | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: BodyKey) -> bytes | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: BodyKey, default: T) -> bytes | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: ContentTypeKey) -> tuple[str, dict[str, str]] | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: ContentTypeKey, default: T) -> tuple[str, dict[str, str]] | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: CookiesKey) -> dict[str, str] | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: CookiesKey, default: T) -> dict[str, str] | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: CsrfTokenKey) -> str | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: CsrfTokenKey, default: T) -> str | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: DependencyCacheKey) -> dict[str, Any] | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: DependencyCacheKey, default: T) -> dict[str, Any] | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: DoCacheKey) -> bool | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: DoCacheKey, default: T) -> bool | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: FormKey) -> dict[str, str | list[str]] | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: FormKey, default: T) -> dict[str, str | list[str]] | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: HttpResponseBodyKey) -> HTTPResponseBodyEvent | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: HttpResponseBodyKey, default: T) -> HTTPResponseBodyEvent | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: HttpResponseStartKey) -> HTTPResponseStartEvent | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: HttpResponseStartKey, default: T) -> HTTPResponseStartEvent | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: IsCachedKey) -> bool | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: IsCachedKey, default: T) -> bool | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: JsonKey) -> Any | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: JsonKey, default: T) -> Any | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: MsgpackKey) -> Any | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: MsgpackKey, default: T) -> Any | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: ParsedQueryKey) -> tuple[tuple[str, str], ...] | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: ParsedQueryKey, default: T) -> tuple[tuple[str, str], ...] | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: ResponseCompressedKey) -> bool | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: ResponseCompressedKey, default: T) -> bool | T:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: UrlKey) -> URL | None:
    ...


@overload
def get_litestar_scope_state(scope: Scope, key: UrlKey, default: T) -> URL | T:
    ...


def get_litestar_scope_state(scope: Scope, key: ScopeStateKeyType, default: T | None = None) -> Any | T:
    """Get an internal value from connection scope state.

    Args:
        scope: The connection scope.
        key: Key to get from internal namespace in scope state.
        default: Default value to return.

    Returns:
        Value mapped to ``key`` in internal connection scope namespace.
    """
    namespace = scope["state"].setdefault(SCOPE_STATE_NAMESPACE, {})
    return namespace.get(key, default)
