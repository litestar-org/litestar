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

__all__ = ("set_litestar_scope_state",)

T = TypeVar("T")


@overload
def set_litestar_scope_state(scope: Scope, key: AcceptKey, value: Accept) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: BaseUrlKey, value: URL) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: BodyKey, value: bytes) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: ContentTypeKey, value: tuple[str, dict[str, str]]) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: CookiesKey, value: dict[str, str]) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: CsrfTokenKey, value: str) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: DependencyCacheKey, value: dict[str, Any]) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: DoCacheKey, value: bool) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: FormKey, value: dict[str, str | list[str]]) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: HttpResponseBodyKey, value: HTTPResponseBodyEvent) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: HttpResponseStartKey, value: HTTPResponseStartEvent) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: IsCachedKey, value: bool) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: JsonKey, value: Any) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: MsgpackKey, value: Any) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: ParsedQueryKey, value: tuple[tuple[str, str], ...]) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: ResponseCompressedKey, value: bool) -> None:
    ...


@overload
def set_litestar_scope_state(scope: Scope, key: UrlKey, value: URL) -> None:
    ...


def set_litestar_scope_state(scope: Scope, key: ScopeStateKeyType, value: Any) -> None:
    """Set an internal value in connection scope state.

    Args:
        scope: The connection scope.
        key: Key to set under internal namespace in scope state.
        value: Value for key.
    """
    scope["state"].setdefault(SCOPE_STATE_NAMESPACE, {})[key] = value
