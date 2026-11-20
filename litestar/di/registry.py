from __future__ import annotations

import graphlib
import itertools
import warnings
from dataclasses import dataclass
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, TypeAlias

from litestar.di._helpers import _describe_provider, _format_key, _format_scope_chain
from litestar.di.exceptions import (
    CaptiveDependencyError,
    CircularDependencyError,
    DIRegistrationError,
    DivergenceError,
    DivergenceWarning,
    MissingProviderError,
)
from litestar.di.provider import _DEFAULT_SCOPE, InjectionTarget, Provider

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Iterable, Mapping

    from litestar.di.provider import DependencyKey

__all__ = (
    "_DEFAULT_SCOPES",
    "DIRegistry",
    "ValueGraphDivergence",
    "check_divergence",
)


_DEFAULT_SCOPES: Final = ("app", "request", "handler")


_Predecessors: TypeAlias = "frozenset[Provider]"


@dataclass(frozen=True, slots=True)
class ValueGraphDivergence:
    """Finding of :func:`~litestar.di.check_divergence`: a node at which two registries'
    value graphs diverge. ``provider``, declared under ``key`` by both, has different
    predecessors in ``registry`` than in ``first_registry``
    """

    key: DependencyKey
    provider: Provider
    first_registry: str
    registry: str
    bindings: Mapping[DependencyKey, tuple[Provider | None, Provider | None]]
    """bindings that differ, as ``(first, this)`` per key, ``None`` for an unbound optional dependency"""

    @staticmethod
    def _describe_binding(binding: Provider | None) -> str:
        if binding is None:
            return "<without provider>"
        return _describe_provider(binding)

    def __str__(self) -> str:
        # Registry names are not required to be unique, and two conflicting registries with one
        # name would otherwise produce e.g. "'route' differs from 'route'"
        ours, theirs = repr(self.registry), repr(self.first_registry)
        if self.registry == self.first_registry:
            ours += " (this registry)"
            theirs += " (a different registry with the same name)"
        # TODO: Better error condition description and why this *might* be an issue.
        # Link to docs?
        message = (
            f"Provider {_format_key(self.key)} has different predecessors in registry "
            f"{ours} than in registry {theirs}. Resolution would implicitly create two "
            f"distinct values for this key in the same scope ({self.provider.scope!r})."
        )
        message += "\n  Differing predecessors:"
        for dependency_key in sorted(self.bindings, key=_format_key):
            first, this = self.bindings[dependency_key]
            message += (
                f"\n    {_format_key(dependency_key)}:"
                f"\n      in {ours}: {self._describe_binding(this)}"
                f"\n      in {theirs}: {self._describe_binding(first)}"
            )
        message += f"\n  provider: {_describe_provider(self.provider)}"
        message += (
            "\n  If this is acceptable, you can ignore it: "
            f"check_divergence(..., ignore=[{self.key!r}]). "
            f"Otherwise bind these dependencies identically, or declare a distinct "
            f"provider for {_format_key(self.key)}."
        )
        return message


_REGISTRY_SEQUENCE = itertools.count()
"""Sequence registries and contexts draw from, so that using a registry created after the
outermost context of its chain was entered raises. See
:meth:`DIContext._raise_if_registry_created_after_context_entered`
"""


class DIRegistry:
    """A registry of DI providers."""

    __slots__ = (
        "_created_at",
        "_frozen",
        "_predecessors",
        "_providers",
        "_scope_index",
        "_seeds",
        "_seeds_by_scope",
        "_static_order",
        "name",
        "scopes",
    )

    def __init__(
        self,
        name: str,
        providers: Iterable[Provider],
        scopes: Iterable[str] | None = None,
    ) -> None:
        """A registry of DI providers.

        A registry holds every provider needed to satisfy the keys it declares.

        A registry is mutable until the first time a graph is solved from it, creating a
        :class:`DIContext` or calling :meth:`predecessors_of`, at which point it
        *freezes*, validating the graph and disallowing further registrations.

        Args:
            name: Name of this registry. Only used for debugging purposes in error messages
            providers: Providers available in this registry
            scopes: Available scopes, in order, outermost first. Defaults to :data:`DEFAULT_SCOPES`

        Raises:
            DIRegistrationError: If the scopes or the providers are invalid.

        """
        self.name = name
        self.scopes = _DEFAULT_SCOPES if scopes is None else tuple(scopes)
        self._created_at = next(_REGISTRY_SEQUENCE)

        if not self.scopes:
            raise DIRegistrationError(f"Registry {name!r} was given an empty scope order.")
        if len(set(self.scopes)) != len(self.scopes):
            raise DIRegistrationError(
                f"Registry {name!r} has duplicate scopes in {_format_scope_chain(self.scopes)}. "
                "Scope names must be unique, as they identify a context's a position in the scope order."
            )

        self._scope_index: dict[str, int] = {scope: index for index, scope in enumerate(self.scopes)}
        self._providers: dict[Any, Provider] = {}
        self._seeds: dict[Any, Provider] = {}
        self._frozen = False
        self._static_order: tuple[Any, ...] = ()
        # a provider's predecessors are part of the identity of the values it produces
        # through this registry. these are populated in .freeze()
        self._predecessors: dict[Provider, _Predecessors] = {}
        # the seeds a context of each scope is given values for. populated in .freeze()
        self._seeds_by_scope: dict[str, dict[Any, Provider]] = {}

        for provider in providers:
            self.register(provider)

    def __repr__(self) -> str:
        return (
            f"<{type(self).__name__} name={self.name!r} providers={len(self._providers)}"
            f" frozen={self._frozen!r} at {id(self):#x}>"
        )

    @property
    def is_frozen(self) -> bool:
        return self._frozen

    @property
    def providers(self) -> Mapping[DependencyKey, Provider]:
        """The registry's providers"""
        return MappingProxyType(self._providers)

    def register(
        self,
        provider: Provider,
        override: bool = False,
    ) -> None:
        """Register a provider.

        Args:
            provider: The provider or callable to create a provider instance
            override: If ``False``, trying to register a provider for an already existing
                key raises :exc:`DIRegistrationError`

        Raises:
            DIRegistrationError: If the registry is frozen, the key is a duplicate and ``override``
                is not set, the scope is unknown, or the provider cannot be inspected.

        """
        if self._frozen:
            raise DIRegistrationError(
                f"Cannot register provider at frozen registry {self.name!r}. A "
                "registry is frozen the first time any dependency is solved from it, "
                "to prevent accidental mutation of live contexts and the values held "
                "within them, and to avoid expensive re-computation of the dependency "
                "graph and its associated checks. Register everything before creating "
                "a DIContext, or build an independent registry with the new providers. "
            )

        provider.resolve_signature()

        if provider.scope not in self._scope_index:
            raise DIRegistrationError(
                f"Unknown scope {provider.scope!r}. Cannot register provider "
                f"{_describe_provider(provider)} with scope {provider.scope!r} on "
                f"registry {self.name!r} with declared scopes "
                f"{_format_scope_chain(self.scopes)}"
            )

        existing = self._providers.get(provider.key)
        if existing is not None and not override:
            raise DIRegistrationError(
                f"Cannot register provider {_describe_provider(provider)} at registry "
                f"{self.name!r} for key {_format_key(provider.key)}. Another "
                "provider is already registered for this key: "
                f"{_describe_provider(existing)}. If you wish to override the existing "
                "provider, explicitly set 'override=True'"
            )

        self._providers[provider.key] = provider
        self._seeds.pop(provider.key, None)
        if provider.is_seed:
            self._seeds[provider.key] = provider

    def register_callable(
        self,
        fn: Callable[..., Any],
        key: DependencyKey,
        scope: str | None = None,
        sync_to_thread: bool | None = None,
        override: bool = False,
    ) -> None:
        """Register a callable as a new provider.

        ``fn`` will be wrapped in one :class:`Provider`. The key type is inferred from
        ``key``: A string will be a provider for a ``NamedDependency``, anything else a
        ``TypeDependency``.

        Args:
            fn: The factory callable to create a provider instance from
            key: Key to register under
            scope: Scope of the new provider
            sync_to_thread: Whether a bare sync callable runs in a worker thread: see
                :class:`Provider`
            override: If ``False``, trying to register a provider for an already existing
                key raises :exc:`DIRegistrationError`

        Raises:
            DIRegistrationError: If the registry is frozen, the key is a duplicate and
                ``override`` is not set, the scope is unknown, or the provider cannot be
                inspected.
        """
        provider = Provider(
            fn,
            scope=_DEFAULT_SCOPE if scope is None else scope,
            key=key,
            sync_to_thread=sync_to_thread,
        )
        self.register(provider, override=override)

    def get_provider(self, key: DependencyKey) -> Provider | None:
        """Return the provider for ``key``, or ``None`` if no provider for ``key`` has been registered"""
        return self._providers.get(key)

    def check_target(self, target: Callable[..., Any]) -> None:
        """Check that this registry has a provider for every required dependency of ``target``.

        Args:
            target: A callable or an :class:`InjectionTarget`

        Raises:
            MissingProviderError: If a required dependency of ``target`` has no provider
        """
        injection_target = InjectionTarget._for_callable(target)
        for dependency in injection_target.dependencies:
            if not dependency.optional and dependency.key not in self._providers:
                raise MissingProviderError(
                    dependency.key,
                    registry_name=self.name,
                    known_keys=self._providers,
                    required_by=injection_target,
                )

    def predecessors_of(self, provider: Provider) -> _Predecessors:
        """Return predecessors of ``provider`` as declared in this registry.

        Raises:
            DIRegistrationError: If this registry does not declare ``provider``.
        """
        self.freeze()
        try:
            return self._predecessors[provider]
        except KeyError:
            raise DIRegistrationError(
                f"Registry {self.name!r} does not declare {provider!r}, so it names no node for it."
            ) from None

    def freeze(self) -> None:
        """Freeze the registry and validate the dependency graph.

        Subsequent calls to this method are a no-op.

        Raises:
            MissingProviderError: If any dependency has no registered provider
            CircularDependencyError: If any provider depends on itself, directly or indirectly
            CaptiveDependencyError: If any provider depends on a value from a later scope
        """
        if self._frozen:
            return

        for key, provider in self._providers.items():
            # really just a sanity check, and to catch possible future regressions.
            # registration through the public interface does not allow for this to happen.
            # providers registered under keys different from their own would be used for
            # aliasing, which is specifically not supported, and should be handled by
            # creating a new provider, forwarding the dependency
            if provider.key != key:
                raise DIRegistrationError(
                    f"Provider key mismatch. Provider {_describe_provider(provider)} with key {_format_key(provider.key)} "
                    f"registered for {_format_key(key)} in registry {self.name!r}."
                )

        self._static_order = self._solve_graph(self._providers)

        # TODO: improve naming
        predecessors: dict[Provider, _Predecessors] = {}
        for key in self._static_order:
            provider = self._providers[key]
            beneath: set[Provider] = set()
            for dependency in provider.dependencies:
                bound = self._providers.get(dependency.key)
                if bound is not None:
                    beneath.add(bound)
                    beneath |= predecessors[bound]
            predecessors[provider] = frozenset(beneath)
        self._predecessors = predecessors
        self._seeds_by_scope = {
            scope: {key: provider for key, provider in self._seeds.items() if provider.scope == scope}
            for scope in self.scopes
        }
        self._frozen = True

    @staticmethod
    def _dependency_path(target: Any, edges: Mapping[Any, list[Any]], order: tuple[Any, ...]) -> tuple[Any, ...]:
        """Shortest chain of keys along 'edges' from a root of the graph to 'target'
        'order' is 'edges' sorted dependency-first.

        Only used for error reporting and debugging
        """
        # dependents first. every dependent of a key is settled before the key is, so a
        # key nothing has reached by then is a root.
        depth: dict[Any, int] = {}
        came_from: dict[Any, Any] = {}
        for key in reversed(order):
            below = depth.setdefault(key, 0) + 1
            for dependency_key in edges.get(key, ()):
                if depth.get(dependency_key, below) >= below:
                    depth[dependency_key] = below
                    came_from[dependency_key] = key
        path = [target]
        while path[-1] in came_from:
            path.append(came_from[path[-1]])
        return tuple(reversed(path))

    def _solve_graph(self, providers: dict[Any, Provider]) -> tuple[Any, ...]:
        """Return the solved dependency graph in a static order. Check for cycles,
        missing providers and captive dependencies. The returned graph is
        guaranteed to be safe to resolve in that order.

        Raises:
            CircularDependencyError: If the graph contains a cycle
            MissingProviderError: If a dependency has no provider
            CaptiveDependencyError: If a provider depends on a value from a later scope
        """
        # an edge is a dependency on a bound key, or a required one. unbound optional
        # dependencies are not considered, as they do not take part in the  resolution
        # process. a required key nothing binds is kept (it will be added as a leaf by
        # TopologicalSorter), so the order reaches the gap and, we can report the path
        # to it in the 'MissingProviderError'
        edges = {
            key: [
                dependency.key
                for dependency in provider.dependencies
                if dependency.key in providers or not dependency.optional
            ]
            for key, provider in providers.items()
        }
        try:
            order = tuple(graphlib.TopologicalSorter(edges).static_order())
        except graphlib.CycleError as exc:
            # 'CycleError' reports the cycle, with the first node repeated at the end,
            # but it does so in 'pred -> node' order, whereas we expect 'node -> pred'
            # order, so we have to reverse here
            raise CircularDependencyError(tuple(reversed(exc.args[1])), registry_name=self.name) from exc

        for key, provider in providers.items():
            for dependency_key in edges[key]:
                dependency_provider = providers.get(dependency_key)
                if dependency_provider is None:
                    raise MissingProviderError(
                        dependency_key,
                        path=(*self._dependency_path(key, edges, order), dependency_key),
                        registry_name=self.name,
                        known_keys=providers,
                        required_by=provider,
                    )
                if self._scope_index[dependency_provider.scope] > self._scope_index[provider.scope]:
                    raise CaptiveDependencyError(
                        key,
                        provider=provider,
                        dependency_key=dependency_key,
                        dependency_provider=dependency_provider,
                        scopes=self.scopes,
                        registry_name=self.name,
                    )
        return order


# TODO: Better function name? it's not very descriptive. idk what tho
def check_divergence(
    registries: Iterable[DIRegistry],
    *,
    scopes: Collection[str] | None = None,
    ignore: Iterable[DependencyKey | Provider] | None = None,
    raise_on_divergence: bool = False,
) -> None:
    """Check for divergences in the predecessors of providers shared by ``registries``.

    Why does this matter? A provider registered in one or more registry that, through
    differing predecessors in each registry, will create unique values below the
    lifetimes of its scope.

    .. code-block::

        @provide(scope="app", key="session")
        async def create_session(engine: NamedDependency[Engine]) -> Session:
            with Session(bind=engine) as session:
                yield session

        @provide(scope="app", key="engine")
        async def engine_one() -> str:
            return create_engine(<some params>)

        @provide(scope="app", key="engine")
        async def engine_two() -> str:
            return create_engine(<some other params>)

        alice = DIRegistry("alice", [create_session, engine_one])
        bob = DIRegistry("bob", [create_session, engine_two])

        app_ctx = DIContext(registry=DIRegistry(), scope="app")
        alice_ctx = DIContext(alice, scope="request", parent=app_ctx)
        bob_ctx = DIContext(alice, scope="request", parent=app_ctx)

        await alice_ctx.solve("session")  # there is now an 'engine' and a 'session' in app_ctx
        await bob_ctx.solve("session")  # a distinct 'engine' and a 'session' are created in app_ctx

    In this example, both registries share the provider for the 'session' key, but have
    different providers for the 'engine' key. Since 'session' depends on 'engine', this
    is a divergence. When resolving 'session' through 'alice_ctx' , it must get
    a different 'engine' then when resolved through 'bob_ctx', which the context will
    solve by invoking 'create_session' again, even if a value for its key is already
    present in 'app_ctx'.

    Raises:
        DivergenceError: If ``raise_on_divergence`` is set, at the first finding.

    """
    ignore = set(ignore) if ignore is not None else set()

    seen: dict[Provider, dict[_Predecessors, str]] = {}
    for registry in registries:
        registry.freeze()
        checked = scopes if scopes is not None else (registry.scopes[0],)
        for key in registry._static_order:
            provider = registry._providers[key]
            if provider.scope not in checked:
                continue
            predecessors = registry._predecessors[provider]
            recorded = seen.setdefault(provider, {})
            if predecessors in recorded:
                continue
            if not recorded:
                recorded[predecessors] = registry.name
                continue
            first, first_name = next(iter(recorded.items()))
            recorded[predecessors] = registry.name
            finding = ValueGraphDivergence(
                key=key,
                provider=provider,
                first_registry=first_name,
                registry=registry.name,
                bindings=_divergent_bindings(first, predecessors),
            )

            if provider in ignore or key in ignore:
                continue
            if raise_on_divergence:
                raise DivergenceError(finding)
            warnings.warn(str(finding), DivergenceWarning, stacklevel=3)


def _divergent_bindings(
    first: _Predecessors, this: _Predecessors
) -> dict[Any, tuple[Provider | None, Provider | None]]:
    """Return the bindings two sets of predecessors diverge on, '(first, this)' per key"""
    a, b = {p.key: p for p in first}, {p.key: p for p in this}
    return {key: (a.get(key), b.get(key)) for key in a.keys() | b.keys() if a.get(key) is not b.get(key)}
