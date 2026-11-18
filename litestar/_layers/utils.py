from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING

from litestar.datastructures.cookie import Cookie
from litestar.datastructures.response_header import ResponseHeader
from litestar.di._helpers import _describe_provider, _format_key
from litestar.di.exceptions import DIRegistrationError

__all__ = ("narrow_dependencies", "narrow_response_cookies", "narrow_response_headers")


if TYPE_CHECKING:
    from litestar.di import DependencyKey, Provide, Provider
    from litestar.types.callable_types import AnyCallable
    from litestar.types.composite_types import Dependencies, ResponseCookies, ResponseHeaders


def narrow_dependencies(dependencies: Dependencies | None) -> dict[DependencyKey, Provider | Provide | AnyCallable]:
    """Given :class:`.types.Dependencies` as a sequence of providers, create a dictionary of them by their key,
    otherwise return a dictionary of ``dependencies``

    Raises:
        DIRegistrationError: If two items of the sequence have the same key.
    """
    if dependencies is None or isinstance(dependencies, Mapping):
        return dict(dependencies or {})
    providers: dict[DependencyKey, Provider] = {}
    for provider in dependencies:
        if (existing := providers.get(provider.key)) is not None:
            raise DIRegistrationError(
                f"Cannot register provider {_describe_provider(provider)} for key {_format_key(provider.key)}. "
                f"The sequence of dependencies already holds a provider for this key: {_describe_provider(existing)}"
            )
        providers[provider.key] = provider
    return dict(providers)


def narrow_response_headers(headers: ResponseHeaders | None) -> Sequence[ResponseHeader]:
    """Given :class:`.types.ResponseHeaders` as a :class:`typing.Mapping`, create a tuple of
    :class:`.datastructures.response_header.ResponseHeader` from it, otherwise return ``headers`` unchanged
    """
    return (
        tuple(ResponseHeader(name=name, value=value) for name, value in headers.items())
        if isinstance(headers, Mapping)
        else headers
    ) or ()


def narrow_response_cookies(cookies: ResponseCookies | None) -> Sequence[Cookie]:
    """Given :class:`.types.ResponseCookies` as a :class:`typing.Mapping`, create a list of
    :class:`.datastructures.cookie.Cookie` from it, otherwise return ``cookies`` unchanged
    """
    return (
        tuple(Cookie(key=key, value=value) for key, value in cookies.items())
        if isinstance(cookies, Mapping)
        else cookies
    ) or ()
