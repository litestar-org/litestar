from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar.di._helpers import (
    _describe_callable,
    _describe_provider,
    _format_key,
    _format_scope_chain,
    _suggest_key,
)
from litestar.exceptions import LitestarException, LitestarWarning

if TYPE_CHECKING:
    from collections.abc import Iterable

    from litestar.di.context import DIContext
    from litestar.di.provider import InjectionTarget, Provider
    from litestar.di.registry import ValueGraphDivergence

__all__ = (
    "CaptiveDependencyError",
    "CircularDependencyError",
    "DIContextClosedError",
    "DIException",
    "DIGraphError",
    "DIRegistrationError",
    "DIResolutionError",
    "DIScopeError",
    "DivergenceError",
    "DivergenceWarning",
    "MissingProviderError",
    "MissingSeedError",
    "ScopeMismatchError",
)


def _format_key_chain(path: tuple[Any, ...]) -> str:
    return " -> ".join(_format_key(key) for key in path)


class DIException(LitestarException):
    pass


class DIRegistrationError(DIException):
    pass


class DIGraphError(DIException):
    pass


class MissingProviderError(DIGraphError):
    """A dependency has no provider registered in the registry"""

    def __init__(
        self,
        key: Any,
        *,
        path: tuple[Any, ...] = (),
        registry_name: str | None = None,
        known_keys: Iterable[Any] = (),
        required_by: Provider | InjectionTarget | None = None,
    ) -> None:
        self.key = key
        self.path = path
        self.registry_name = registry_name

        subject = (
            "No provider is registered" if registry_name is None else f"Registry {registry_name!r} has no provider"
        )
        message = f"{subject} for dependency {_format_key(key)}."
        if required_by is not None:
            message += f"\n  required by: {_describe_callable(required_by.fn)}"
        if len(path) > 1:
            message += f"\n  dependency path: {_format_key_chain(path)}"
        message += _suggest_key(key, known_keys)
        super().__init__(message)


class CircularDependencyError(DIGraphError):
    def __init__(self, cycle: tuple[Any, ...], *, registry_name: str | None = None) -> None:
        self.cycle = cycle
        self.registry_name = registry_name

        message = f"Circular dependency detected: {_format_key_chain(cycle)}."
        message += "\n  Every provider in this cycle depends on itself, directly or indirectly,"
        message += "\n  so none of them can ever be resolved. Break the cycle by removing one of"
        message += "\n  these dependencies."
        if registry_name is not None:
            message += f"\n  registry: {registry_name!r}"
        super().__init__(message)


class CaptiveDependencyError(DIGraphError):
    """A provider depends on a value from a later scope, which it would keep using
    after that value was cleaned up
    """

    def __init__(
        self,
        key: Any,
        *,
        provider: Provider,
        dependency_key: Any,
        dependency_provider: Provider,
        scopes: tuple[str, ...],
        registry_name: str,
    ) -> None:
        self.key = key
        self.dependency_key = dependency_key
        self.registry_name = registry_name

        message = (
            f"Provider {_format_key(key)} with scope {provider.scope!r} depends on "
            f"{_format_key(dependency_key)} with scope {dependency_provider.scope!r}. "
            f"Since scope {dependency_provider.scope!r} descends from scope {provider.scope!r}, "
            f"providers with scope {provider.scope!r} cannot depend on values from "
            f"scope {dependency_provider.scope!r}"
        )
        message += f"\n  provider:   {_describe_provider(provider)}"
        message += f"\n  dependency: {_describe_provider(dependency_provider)}"
        message += f"\n  scope order: {_format_scope_chain(scopes)}"
        message += f"\n  registry: {registry_name!r}"
        super().__init__(message)


class DIResolutionError(DIException):
    pass


class ScopeMismatchError(DIResolutionError):
    """A provider exists, but its scope is not entered by the requesting context or any context
    above it
    """

    def __init__(
        self,
        key: Any,
        *,
        provider: Provider,
        context_scope: str,
        entered_scopes: tuple[str, ...],
        scopes: tuple[str, ...],
        registry_name: str,
    ) -> None:
        self.key = key
        self.provider = provider
        self.context_scope = context_scope
        self.entered_scopes = entered_scopes

        message = (
            f"Cannot resolve dependency {_format_key(key)} through scope {context_scope!r}. "
            f"Its scope {provider.scope!r} does not match that of the current context, "
            f"or any of its parents."
        )
        message += f"\n  provider: {_describe_provider(provider)}"
        message += f"\n  entered scopes: {_format_scope_chain(entered_scopes)}"
        message += f"\n  scope order: {_format_scope_chain(scopes)}"
        super().__init__(message)


class DivergenceError(DIGraphError):
    """Covering a :class:`ValueGraphDivergence`"""

    def __init__(self, finding: ValueGraphDivergence) -> None:
        self.finding = finding
        super().__init__(str(finding))


class DivergenceWarning(LitestarWarning):
    """Covering a :class:`ValueGraphDivergence`"""


class MissingSeedError(DIResolutionError):
    """A context was built without a value for a seed key its registry declares at its scope"""

    def __init__(
        self, key: Any, *, provider: Provider, seeded: Iterable[Any], owner: DIContext, registry_name: str
    ) -> None:
        self.key = key
        self.provider = provider
        self.registry_name = registry_name

        message = (
            f"Registry {registry_name!r} declares {_format_key(key)} as a seed at scope"
            f" {provider.scope!r}, but context {owner} was not provided the value."
            f" (seeded={[_format_key(seeded_key) for seeded_key in seeded]})"
        )
        super().__init__(message)


class DIScopeError(DIResolutionError):
    """A scope was entered out of order, skipped, repeated, not at all, does not exist"""


class DIContextClosedError(DIResolutionError):
    """A :class:`DIContext` was used after it was closed."""
