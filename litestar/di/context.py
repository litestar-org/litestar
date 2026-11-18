# pyright: reportUnnecessaryTypeIgnoreComment=false
from __future__ import annotations

import asyncio
import contextvars
import sys
from typing import (
    TYPE_CHECKING,
    Any,
    Final,
    Self,
    TypeVar,
    overload,
)

from litestar.di._helpers import (
    _bounded_repr,
    _describe_callable,
    _describe_provider,
    _format_key,
    _format_scope_chain,
    _suggest_key,
)
from litestar.di.exceptions import (
    DIContextClosedError,
    DIException,
    DIRegistrationError,
    DIResolutionError,
    DIScopeError,
    MissingProviderError,
    MissingSeedError,
    ScopeMismatchError,
)
from litestar.di.provider import InjectionTarget
from litestar.di.registry import _REGISTRY_SEQUENCE

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable, Collection, Mapping
    from contextlib import AbstractAsyncContextManager
    from types import TracebackType

    from litestar.di.provider import DependencyKey, InjectionParameter, Provider
    from litestar.di.registry import DIRegistry, _Predecessors

__all__ = ("DIContext", "PreparedDIContext")


_IS_PY_313_PLUS: Final = sys.version_info >= (3, 13)


T = TypeVar("T")
T1 = TypeVar("T1")
T2 = TypeVar("T2")
T3 = TypeVar("T3")


_CTX_RUNNING_PROVIDER_SLOT: contextvars.ContextVar[_ProviderSlot | None] = contextvars.ContextVar(
    "di_producing", default=None
)
"""_ProviderSlot running in the current context"""


class _ProviderSlot:
    """Mutable provider state, stored per DIContext.

    Acts as a proxy to the provider, produced value, as well as a guard and lock around
    the factory invocation. Placed in the DIContext instead of the actual value.
    """

    __slots__ = ("_lock", "done", "provider", "running", "value")

    def __init__(self, provider: Provider) -> None:
        self.provider = provider
        self.value: Any = None
        self.done = False
        # whether a production is currently running. used by
        # DIContext._raise_if_inside_running_provider to raise for a factory reaching back into
        # the context
        self.running = False
        # lazily created, since it does come with a cost
        self._lock: asyncio.Lock | None = None

    def get_lock(self) -> asyncio.Lock:
        if (lock := self._lock) is None:
            lock = self._lock = asyncio.Lock()
        return lock

    def __repr__(self) -> str:
        state = "resolved" if self.done else "producing" if self.running else "empty"
        value = f" value={_bounded_repr.repr(self.value)}" if self.done else ""
        return f"<{type(self).__name__} [{state}] provider={self.provider!r}{value} at {id(self):#x}>"

    def set_result(self, value: Any) -> None:
        self.value = value
        self.done = True


class DIContext:
    """A live DI scope. Manages resolution and lifetime of dependencies"""

    __slots__ = (
        "_children",
        "_cleanup_stack",
        "_entered",
        "_entered_at",
        "_seed_values",
        "_slots",
        "closed",
        "parent",
        "registry",
        "scope",
    )

    closed: bool
    parent: DIContext | None
    registry: DIRegistry
    scope: str

    def __init__(
        self,
        registry: DIRegistry,
        scope: str | None = None,
        parent: DIContext | None = None,
        seeds: Mapping[DependencyKey, Any] | None = None,
        prepared: PreparedDIContext | None = None,
    ) -> None:
        """A DI context to resolve dependencies.

        If ``scope`` is not given, the outermost scope is used, or, when ``parent`` is
        given, the scope immediately following the parent's. Creating a context freezes
        ``registry``.

        Args:
            registry: The registry to resolve through
            scope: The scope this context owns
            parent: The context before this
            seeds: Values for the seed keys of this scope. If ``registry`` declares seeds,
                values for all seeds must be given
            prepared: The :class:`PreparedDIContext` of ``registry``, ``scope`` and ``parent``,
                which has checked them. If not given, it is created
        """
        if prepared is None:
            prepared = PreparedDIContext(registry, scope, parent)
        registry = self.registry = prepared.registry
        scope = self.scope = prepared.scope
        self.parent = parent
        self.closed = False
        self._entered = False
        self._entered_at = 0
        # created with the first generator provider this context enters
        self._cleanup_stack: _CleanupStack | None = None
        # keep track of children to prevent out-of-order closing (which can only happen
        # when the context isn't used as a context manager). created with the first child
        self._children: set[DIContext] | None = None

        # dependency state. keyed by node of the value graph, provider, predecessors
        self._slots: dict[tuple[Provider, _Predecessors], _ProviderSlot] = {}

        # the values of the seeds given to this context and to the contexts before it, by
        # their declaration. a seed has no slot
        self._seed_values: dict[Provider, Any] = parent._seed_values if parent is not None else {}
        declared = registry._seeds_by_scope[scope]
        if seeds or declared:
            seeds = seeds or {}
            seed_values = self._seed_values = self._seed_values.copy()
            try:
                for key, declaration in declared.items():
                    seed_values[declaration] = seeds[key]
            except KeyError:
                raise self._seed_error(seeds, declared) from None
            if len(seeds) != len(declared):
                raise self._seed_error(seeds, declared)

    @property
    def _entered_scopes(self) -> tuple[str, ...]:
        return self.registry.scopes[: self.registry._scope_index[self.scope] + 1]

    def __repr__(self) -> str:
        state = "closed" if self.closed else "open" if self._entered else "not entered"
        return (
            f"<{type(self).__name__} [{state}] scope={self.scope!r} registry={self.registry.name!r} at {id(self):#x}>"
        )

    @overload
    async def inject(
        self,
        fn: Callable[..., Awaitable[T]],
        args: tuple[Any, ...] = (),
        kwargs: Mapping[str, Any] | None = None,
        *,
        sync_to_thread: bool | None = None,
    ) -> T: ...

    @overload
    async def inject(
        self,
        fn: Callable[..., T],
        args: tuple[Any, ...] = (),
        kwargs: Mapping[str, Any] | None = None,
        *,
        sync_to_thread: bool | None = None,
    ) -> T: ...

    async def inject(
        self,
        fn: Callable[..., Any],
        args: tuple[Any, ...] = (),
        kwargs: Mapping[str, Any] | None = None,
        *,
        sync_to_thread: bool | None = None,
    ) -> Any:
        """Resolve all dependencies of ``fn``, inject them into ``fn``, and return its
        return value.

        ``args`` and ``kwargs`` are passed to ``fn``. When a parameter is declared a
        dependency but still passed explicitly, the explicit form will take precedence.

        This method should not be used from within a dependency provider, as it can
        result in deadlocks: When solved dynamically, a dependency can request itself,
        creating a cycle, which can only be checked exhaustively if all dependencies
        are declared upfront. A best-effort check is performed to prevent calling this
        method from within a dependency, but it should not be relied on.

        Args:
            fn: A callable or an :class:`InjectionTarget`
            args: Positional arguments for ``fn``
            kwargs: Keyword arguments for ``fn``
            sync_to_thread: Whether a synchronous ``fn`` runs in a worker thread

        Raises:
            MissingProviderError: If a required dependency has no provider.
            DIResolutionError: If the call is found to come from inside a factory; a best effort
                check to avoid misuse, see :doc:`/usage/di_2/caveats`.
        """
        self._check_usable(for_method="inject")
        target = InjectionTarget._for_callable(fn)
        call_kwargs = dict(kwargs) if kwargs else {}
        supplied = call_kwargs.keys() | set(target._positional_names[: len(args)])
        await self._resolve_arguments(target.dependencies, call_kwargs, supplied=supplied)
        return await target._call(args, call_kwargs, sync_to_thread=sync_to_thread)

    async def solve_arguments(self, fn: Callable[..., Any], *, supplied: Collection[str] = ()) -> dict[str, Any]:
        """Return the resolved dependencies of ``fn``, keyed by parameter name.

        Parameters in ``supplied`` and optional dependencies without a provider are left out.

        Args:
            fn: A callable or an :class:`InjectionTarget`
            supplied: Names of parameters not to be resolved

        Raises:
            MissingProviderError: If a required dependency has no provider.
            DIResolutionError: If ``supplied`` names a parameter ``fn`` does not declare, unless
                ``fn`` takes ``**kwargs``; or if the call is found to come from inside a factory,
                a best effort check to avoid misuse, see :doc:`/usage/di_2/caveats`.
        """
        self._check_usable(for_method="solve_arguments")
        target = InjectionTarget._for_callable(fn)
        if not target._takes_any_keyword and not target._parameter_names.issuperset(supplied):
            undeclared = ", ".join(repr(name) for name in sorted(set(supplied) - target._parameter_names))
            raise DIResolutionError(
                f"Cannot solve the arguments of {_describe_callable(target.fn)}: 'supplied' names "
                f"parameters it does not declare: {undeclared}"
            )
        arguments: dict[str, Any] = {}
        await self._resolve_arguments(target.dependencies, arguments, supplied=supplied)
        return arguments

    @overload
    async def solve_many(self, key1: type[T1], /) -> tuple[T1]: ...

    @overload
    async def solve_many(self, key1: type[T1], key2: type[T2], /) -> tuple[T1, T2]: ...

    @overload
    async def solve_many(self, key1: type[T1], key2: type[T2], key3: type[T3], /) -> tuple[T1, T2, T3]: ...

    @overload
    async def solve_many(self, *keys: DependencyKey) -> tuple[Any, ...]: ...

    async def solve_many(self, *keys: DependencyKey) -> tuple[Any, ...]:
        """Solve all ``keys``, and return their resolved values in the order of ``keys``.

        This method should not be used from within a dependency provider, as it can
        result in deadlocks: When solved dynamically, a dependency can request itself,
        creating a cycle, which can only be checked exhaustively if all dependencies
        are declared upfront. A best-effort check is performed to prevent calling this
        method from within a dependency, but it should not be relied on.

        Raises:
            MissingProviderError: If a key has no provider.
            DIResolutionError: If the call is found to come from inside a factory; a
                best effort check to avoid misuse, see :doc:`/usage/di_2/caveats`.
        """
        self._check_usable(for_method="solve_many")
        return tuple([await self._resolve_one(key) for key in keys])

    @overload
    async def solve(self, key: type[T]) -> T: ...

    @overload
    async def solve(self, key: str) -> Any: ...

    async def solve(self, key: DependencyKey) -> Any:
        """Solve for ``key`` and return its value.

        This method should not be used from within a dependency provider, as it can
        result in deadlocks: When solved dynamically, a dependency can request itself,
        creating a cycle, which can only be checked exhaustively if all dependencies
        are declared upfront. A best-effort check is performed to prevent calling this
        method from within a dependency, but it should not be relied on.

        Raises:
            MissingProviderError: If a key has no provider.
            DIResolutionError: If the call is found to come from inside a factory; a best effort
                check to avoid misuse, see :doc:`/usage/di_2/caveats`.
        """
        self._check_usable(for_method="solve")
        return await self._resolve_one(key)

    @overload
    def get(self, key: type[T]) -> T: ...

    @overload
    def get(self, key: str) -> Any: ...

    def get(self, key: DependencyKey) -> Any:
        """Return the previously solved value of ``key``.

        Raises:
            DIResolutionError: If the key has not been resolved in this context or a parent

        """
        # simply getting an already solved dependency cannot deadlock, so we allow
        # reach backs
        self._check_usable(allow_running_inside_provider=True)

        provider = self.registry._providers.get(key)
        if provider is not None:
            if provider in self._seed_values:
                return self._seed_values[provider]
            owner = self._get_context_for_scope(provider.scope)
            if owner is not None:
                slot = owner._slots.get((provider, self.registry._predecessors[provider]))
                if slot is not None and slot.done:
                    # the value get closed with its owner, which could be a parent context
                    # closed out-of-order while this one is still open
                    owner._raise_if_closed()
                    return slot.value

        raise DIResolutionError(
            f"Cannot statically get {_format_key(key)}. It has not been resolved in "
            f"{self!r} or any of its parents. entered scopes: {_format_scope_chain(self._entered_scopes)}"
        )

    def has_solved(self, key: DependencyKey) -> bool:
        provider = self.registry._providers.get(key)
        if provider is None:
            return False
        if provider in self._seed_values:
            return provider.scope == self.scope
        predecessors = self.registry._predecessors[provider]
        slot = self._slots.get((provider, predecessors))
        if slot is None:
            return False
        return slot.done

    async def __aenter__(self) -> Self:
        """Open this context.

        A context can only be entered once. Closing and re-entering it again is an error.

        Raises:
            DIContextClosedError: If this context, or its parent context, has already been closed
            DIScopeError: If it has already been entered, or its parent has not been
        """
        self._raise_if_closed()
        if self._entered:
            raise DIScopeError(
                f"{self!r} has already been entered. To build a nested context, use 'async with ctx.enter_nested(...)'"
            )
        if self.parent is not None:
            self.parent._check_usable(allow_running_inside_provider=True)
        self._entered = True
        self._entered_at = next(_REGISTRY_SEQUENCE)
        if self.parent is not None:
            if self.parent._children is None:
                self.parent._children = set()
            self.parent._children.add(self)
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Close this context and clean up all its dependencies"""
        await self._close(exc_type, exc, traceback)

    async def _close(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self.closed:
            return

        # set before any 'await'
        self.closed = True

        # a production still running raises DIContextClosedError once it finishes:
        # '_CleanupStack' on a late resource, '_produce' on a late value
        try:
            if self._cleanup_stack is not None:
                await self._cleanup_stack.aclose(exc_type, exc, traceback)
        finally:
            if self.parent is not None and self.parent._children is not None:
                self.parent._children.discard(self)
            # a child context outliving its parent is a bug and can lead to weird
            # consequences. we report this after teardown, so we can be sure about the state
            if self._children:
                not_closed = ", ".join(repr(child) for child in self._children)
                raise DIScopeError(
                    f"{self!r} was closed while {len(self._children)} nested context(s) under "
                    f"it had not yet been closed: {not_closed}. DIContexts should always close "
                    "in the reverse order they are opened in. Closing them out of order could "
                    "result in a value in a nested context may depending on one from its parent "
                    "context, which closes while its dependencies outlive it. Ensure all nested "
                    "DIContexts are closed before their parents. DIContext created inside a "
                    "task or a generator should close inside that block."
                )
            if self._entered and self.parent is not None and self.parent.closed:
                raise DIScopeError(
                    f"{self!r} was closed after its parent {self.parent!r}. DIContexts should "
                    "always close in the reverse order they are opened in. This context has been "
                    "closed, but its parent closed first."
                )

    def enter_nested(
        self,
        registry: DIRegistry | None = None,
        scope: str | None = None,
        seeds: Mapping[DependencyKey, Any] | None = None,
    ) -> DIContext:
        """A new :class:`DIContext`, with this instance set as its parent.

        .. code-block:: python

            async with app_context.enter_nested() as request_context:
                ...

        Args:
            registry: The registry the child resolves through. Defaults to this context's
            scope: The scope to enter. Defaults to the one immediately following this context's
            seeds: Values for the seed keys of the nested scope
        """
        return DIContext(self.registry if registry is None else registry, scope=scope, parent=self, seeds=seeds)

    def _raise_if_registry_created_after_context_entered(self, registry: DIRegistry) -> None:
        outermost = self
        while outermost.parent is not None:
            outermost = outermost.parent
        if outermost._entered and registry._created_at > outermost._entered_at:
            raise DIRegistrationError(
                f"Registry {registry.name!r} was created after {outermost!r} was entered, "
                "so it cannot be used beneath it. Registries of a chain must be created "
                "before a context using them is entered"
            )

    def _raise_if_inside_running_provider(self, for_method: str | None) -> None:
        """Raise if being called from inside a provider.

        Best effort check using context variables, not guaranteed to always work.

        See for details :doc:`/usage/di_2/caveats`
        """
        current_provider = _CTX_RUNNING_PROVIDER_SLOT.get()
        if current_provider is not None and current_provider.running:
            target = f"'DIContext.{for_method}()' of " if for_method else ""
            target += repr(self)
            raise DIResolutionError(
                f"{target} used from inside the provider producing "
                f"{_format_key(current_provider.provider.key)}. A provider resolving "
                "dependencies dynamically may deadlock by creating a cycle. Declare "
                "its dependencies as parameters instead"
            )

    def _raise_if_closed(self) -> None:
        if self.closed:
            raise DIContextClosedError(f"{self!r} is closed and can no longer resolve or provide dependencies")

    def _raise_if_context_in_chain_closed(self) -> None:
        self._raise_if_closed()
        context = self.parent
        while context is not None:
            if context.closed:
                raise DIContextClosedError(
                    f"{self!r} cannot be used, because a parent context of it is closed: {context!r}"
                )
            context = context.parent

    def _check_usable(
        self,
        *,
        allow_running_inside_provider: bool = False,
        for_method: str | None = None,
    ) -> None:
        if not allow_running_inside_provider:
            self._raise_if_inside_running_provider(for_method)
        self._raise_if_context_in_chain_closed()
        if not self._entered:
            raise DIScopeError(f"{self!r} has not been entered, so it cannot resolve dependencies")

    def _get_context_for_scope(self, scope: str) -> DIContext | None:
        """Return the context in this chain that owns ``scope``"""
        context: DIContext | None = self
        while context is not None:
            if context.scope == scope:
                return context
            context = context.parent
        return None

    def _get_or_create_slot_for(self, provider: Provider, predecessors: _Predecessors) -> _ProviderSlot:
        try:
            slot = self._slots[(provider, predecessors)]
        except KeyError:
            slot = self._slots[provider, predecessors] = _ProviderSlot(provider)
        return slot

    def _seed_error(
        self, seeds: Mapping[DependencyKey, Any], declared: Mapping[DependencyKey, Provider]
    ) -> DIException:
        """Return the error of ``seeds`` not matching ``declared``, the seeds of this context's
        scope: a seed passed for a key that is not a seed at this scope, else a declared seed
        that was not passed.
        """
        registry = self.registry
        for key in seeds:
            if key in declared:
                continue
            try:
                provider = registry._providers[key]
            except KeyError:
                detail = (
                    f"nothing is registered for it. {_suggest_key(key, declared)} ."
                    f"Declare it as Provider.seed({key!r}, scope={self.scope!r}), or drop the seed."
                )
            else:
                if provider.is_seed:
                    detail = (
                        f"it is declared as a seed at scope {provider.scope!r}. Pass it to the context "
                        f"with scope {provider.scope!r} instead, or declare its provider with scope={self.scope!r}."
                    )
                else:
                    detail = (
                        f"it is produced by provider {_describe_provider(provider)}. Register it in place of this one."
                    )
            listed = ", ".join(_format_key(declared_key) for declared_key in declared) or "nothing"
            return DIRegistrationError(
                f"{self!r} was seeded with {_format_key(key)}, which registry {registry.name!r} does "
                f"not declare as a seed at scope {self.scope!r}: {detail} declared here: {listed}"
            )

        key = next(key for key in declared if key not in seeds)
        return MissingSeedError(key, provider=declared[key], seeded=seeds, owner=self, registry_name=registry.name)

    async def _resolve_one(self, key: DependencyKey) -> Any:
        """Solve for 'key' and return its value"""
        try:
            provider = self.registry._providers[key]
        except KeyError:
            raise self._lookup_error(key) from None
        if provider in self._seed_values:
            return self._seed_values[provider]
        return await self._resolve_provider(provider)

    async def _resolve_provider(self, provider: Provider) -> Any:
        """Return the value of 'provider', which is not a seed with a value. Produce it if no
        value exists
        """
        owning_context = self._get_context_for_scope(provider.scope)
        if owning_context is None:
            raise self._lookup_error(provider.key)

        # the value lives at 'owning_context' and dies with it, so 'owner' is what has
        # to be open
        owning_context._raise_if_closed()
        slot = owning_context._get_or_create_slot_for(provider, self.registry._predecessors[provider])

        if slot.done:
            # the default case once a value exists
            return slot.value

        # performance: the lock is held while the provider *and* its dependencies are
        # resolved. a concurrent attempt to solve 'provider' must wait at the lock for
        # this duration. this is a rare case though, as it can only happen for
        # app-scoped providers, or concurrent tasks that share a context.
        async with slot.get_lock():
            if slot.done:
                # mypy narrows the attribute across the await. it actually did change,
                # produced by whoever held the lock before this caller
                return slot.value  # type: ignore[unreachable]
            # taking the lock may have suspended, and the owner might have closed in the meantime
            owning_context._raise_if_closed()
            slot.running = True
            try:
                kwargs: dict[str, Any] = {}
                # performance: _resolve_arguments recurses into _resolve_provider
                # eventually if necessary to solve sub-dependencies. it would be
                # possible to unroll this into a flat loop (we know the necessary order
                # statically), but this comes at the cost of an always-eager resolution,
                # which is slower for the most common cases. it's only faster when
                # there's a deep dependency chain, which is uncommon.
                await self._resolve_arguments(provider.dependencies, kwargs)
                if owning_context.closed:
                    # owner closed during resolution
                    raise DIContextClosedError(
                        f"{owning_context!r} was closed while resolving {_format_key(provider.key)} "
                        f"from provider {_describe_callable(provider.fn)}"
                    )
                cleanup_stack = owning_context._cleanup_stack
                if cleanup_stack is None and provider._context_manager_factory is not None:
                    cleanup_stack = owning_context._cleanup_stack = _CleanupStack()
                token = _CTX_RUNNING_PROVIDER_SLOT.set(slot)
                try:
                    value = await provider._produce(kwargs, cleanup_stack)
                except BaseException as exc:
                    exc.add_note(
                        f"Raised while resolving dependency {_format_key(provider.key)}"
                        f" (scope={provider.scope!r}, provider={_describe_provider(provider)})."
                    )
                    raise
                finally:
                    _CTX_RUNNING_PROVIDER_SLOT.reset(token)
                if owning_context.closed:
                    # owner closed during resolution
                    raise DIContextClosedError(
                        f"{owning_context!r} was closed while resolving {_format_key(provider.key)} "
                        f"from provider {_describe_callable(provider.fn)}"
                    )
                # mypy takes a name bound in a 'try' that is nested in a 'try/finally' as
                # possibly undefined after it, although the 'except' above always raises
                slot.set_result(value)  # type: ignore[possibly-undefined]
            finally:
                slot.running = False
            return slot.value

    async def _resolve_arguments(
        self,
        dependencies: tuple[InjectionParameter, ...],
        kwargs: dict[str, Any],
        supplied: Collection[str] = (),
    ) -> None:
        """Resolve each declared dependency into ``kwargs``

        Args:
            dependencies: What the callable declares
            kwargs: Dict where dependencies are resolved into
            supplied: Parameters the callee does not need
        """
        providers = self.registry._providers
        seed_values = self._seed_values
        for dependency in dependencies:
            # anything the caller decided is neither resolved nor looked up
            if dependency.parameter_name in supplied:
                continue
            provider = providers.get(dependency.key)
            if provider is None:
                # ignore optional dependencies with no provider
                if dependency.optional:
                    continue
                raise self._lookup_error(dependency.key)
            if provider in seed_values:
                # a seed's value is there since the context was built: nothing to await
                kwargs[dependency.parameter_name] = seed_values[provider]
            else:
                kwargs[dependency.parameter_name] = await self._resolve_provider(provider)

    def _lookup_error(self, key: DependencyKey) -> DIException:
        provider = self.registry.get_provider(key)
        known = self.registry._providers

        # only 2 cases:
        # 1. No provider registered for 'key'
        # 2. A provider does exist, but not at this scope. Everything else is ruled
        #    out by the graph validation

        if provider is None:
            return MissingProviderError(key, registry_name=self.registry.name, known_keys=known)

        # a provider whose scope *is* entered always has an owning context to hold its
        # slot. shat's left is a scope mismatch
        return ScopeMismatchError(
            key,
            provider=provider,
            context_scope=self.scope,
            entered_scopes=self._entered_scopes,
            scopes=self.registry.scopes,
            registry_name=self.registry.name,
        )


class PreparedDIContext:
    """Factory to create a DIContext, from a given registry, scope, and parent context"""

    __slots__ = ("registry", "scope")

    registry: DIRegistry
    scope: str

    def __init__(
        self,
        registry: DIRegistry,
        scope: str | None = None,
        parent: DIContext | PreparedDIContext | None = None,
    ) -> None:
        """Prepare contexts of ``registry`` at ``scope``, nested in ``parent``.

        If ``scope`` is not given, the outermost scope is used, or, when ``parent`` is
        given, the scope immediately following the parent's. Freezes ``registry``.

        Args:
            registry: The registry the contexts resolve through
            scope: The scope the contexts own
            parent: The context before these, or its prepared context

        Raises:
            DIScopeError: If ``registry`` and the registry of ``parent`` declare different scopes,
                ``registry`` has no scope ``scope``, or ``scope`` is not the one following the
                scope of ``parent``, without a parent the outermost one
            DIContextClosedError: If ``parent`` is a closed context
            DIRegistrationError: If ``parent`` is a context and ``registry`` was created after
                the outermost context before it was entered
        """
        registry.freeze()
        scopes = registry.scopes
        if parent is not None and scopes != parent.registry.scopes:
            raise DIScopeError(
                f"Cannot nest a context resolving through registry {registry.name!r} inside {parent!r}: "
                f"{registry.name!r} declares scopes {_format_scope_chain(scopes)}, but "
                f"{parent.registry.name!r} declares {_format_scope_chain(parent.registry.scopes)}."
            )
        if scope is None:
            scope = scopes[0] if parent is None else _next_scope(registry, parent.scope)
        if scope not in registry._scope_index:
            raise DIScopeError(
                f"Registry {registry.name!r} has no scope {scope!r}. Known scopes: {_format_scope_chain(scopes)}"
            )
        if parent is None:
            if scope != scopes[0]:
                raise DIScopeError(
                    f"A context without a parent has to use the outermost scope {scopes[0]!r}. "
                    f"Got {scope!r}. Scope order: {_format_scope_chain(scopes)}"
                )
        else:
            if isinstance(parent, DIContext):
                if parent.closed:
                    raise DIContextClosedError(
                        f"Cannot open DIContext for scope {scope!r} with closed parent {parent!r}"
                    )
                if registry is not parent.registry:
                    parent._raise_if_registry_created_after_context_entered(registry)
            if registry._scope_index[scope] != registry._scope_index[parent.scope] + 1:
                raise DIScopeError(
                    f"Cannot enter scope {scope!r} out of order. {scope!r} does not directly follow "
                    f"{parent.scope!r}. scope order: {_format_scope_chain(scopes)}"
                )
        self.registry = registry
        self.scope = scope

    def __repr__(self) -> str:
        return f"<{type(self).__name__} scope={self.scope!r} registry={self.registry.name!r}>"

    def create(self, parent: DIContext | None = None, seeds: Mapping[DependencyKey, Any] | None = None) -> DIContext:
        """Return a new :class:`DIContext` of the registry at the scope.

        Args:
            parent: The context before the new one: a context of the registry and scope of the
                ``parent`` given to this prepared context, with the outermost context entered
                after the registry was created
            seeds: Values for the seed keys of the scope. If the registry declares seeds,
                values for all seeds must be given
        """
        return DIContext(self.registry, self.scope, parent, seeds, self)


class _CleanupStack:
    """Stack to manage cleanup of generator providers opened in a :class:`DIContext`.
    Similar to contextlib.AsyncExitStack, with some additional functionality and
    intentional differences.

    Cleanups run most recently opened first. Contrary to AsyncExitStack, a cleanup
    cannot suppress an exception raised during its execution. A failed cleanup is
    collected and its exception not handed to the cleanups after it. Multiple exceptions
    are grouped into anExceptionGroup.

    An exception always outranks a cancellation, which is noted and, from Python 3.13
    onwards, cancellations are re-armed after everything has been closed.
    """

    __slots__ = ("_closed", "_entries")

    def __init__(self) -> None:
        self._entries: list[tuple[AbstractAsyncContextManager[Any], Provider]] = []
        self._closed = False

    async def enter_async_context(self, context_manager: AbstractAsyncContextManager[Any], provider: Provider) -> Any:
        """Enter 'context_manager' and close it when this stack closes.

        Raises:
            DIContextClosedError: If the stack has already been unwound
            BaseException: What closing the resource again raised, if that failed. it is
                raised in place of the DIContextClosedError and carries a note saying why the
                resource was closed
        """
        if self._closed:
            raise DIContextClosedError(
                f"Cannot create {_format_key(provider.key)} in closed DIContext. "
                f"(provider={_describe_callable(provider.fn)})"
            )

        value = await context_manager.__aenter__()

        if self._closed:
            # closed during '__aenter__'. this can happen because __aenter__ might be
            # suspended while entering and closed elsewhere during that time. the
            # factory has been called by now, so its resources still must be closed
            # properly.
            try:  # type: ignore[unreachable]  # mypy narrows the attribute across the await
                await context_manager.__aexit__(None, None, None)
            except BaseException as cleanup_error:
                cleanup_error.add_note(
                    f"Raised while closing {_format_key(provider.key)} "
                    f"(scope={provider.scope!r}, provider={_describe_callable(provider.fn)}): its "
                    "DIContext closed while the provider was being invoked."
                )
                raise
            # we still want to raise, because this is probably buggy behaviour on the
            # application side
            raise DIContextClosedError(
                f"Dependency {_format_key(provider.key)} was closed again as soon as it "
                "was created: its DIContext closed while it was being invoked. "
                f"(provider={_describe_callable(provider.fn)})"
            )

        self._entries.append((context_manager, provider))
        return value

    async def aclose(
        self,
        exc_type: type[BaseException] | None = None,
        exc: BaseException | None = None,
        traceback: TracebackType | None = None,
    ) -> None:
        """Close things. LIFO order.

        Cleanups always run independently of other cleanups. If one cleanup raises, its
        exception will be collected and raised as part of an :ecx:`ExceptionGroup`.

        If there's an outer exception (`exc`), it will be thrown into the generators.

        A cancellation delivered during a cleanup does not cancel the teardown.
        Remaining cleanups still run, and the :exc:`asyncio.CancelledError` is thrown
        into them. It will always be re-raised after they finished. From Python 3.13 the
        task is re-cancelled as well when it has a cancellation request outstanding, so
        the cancellation is delivered at the next 'await'.

        Why shield teardown from cancellation? Because then its behaviour becomes
        unexpected. If, for example, a teardown performs a database commit, it might be
        cancelled in-fight, leaving the application in a broken state.

        Raises:
            BaseExceptionGroup: If more than one cleanup failed
            BaseException: If exactly one cleanup failed, that failure, unwrapped
        """
        errors: list[BaseException] = []
        cancelled_error: asyncio.CancelledError | None = None
        cancelled_provider: Provider | None = None
        self._closed = True

        # LIFO order, matching the reverse dependency creation order
        while self._entries:
            context_manager, provider = self._entries.pop()
            try:
                await context_manager.__aexit__(exc_type, exc, traceback)
            except asyncio.CancelledError as cancellation:
                # teardown was cancelled, or this cleanup raised the cancellation
                # itself
                cancellation.add_note(
                    f"Delivered while tearing down dependency {_format_key(provider.key)}"
                    f" (scope={provider.scope!r}, provider={_describe_callable(provider.fn)})."
                )
                cancelled_error, cancelled_provider = cancellation, provider
                exc_type, exc, traceback = type(cancellation), cancellation, cancellation.__traceback__
            except BaseException as cleanup_error:  # noqa: BLE001
                # this is where contextlib.asynccontextmanager reports a generator that
                # yielded more than once. That message says nothing about which provider
                # this occurred in, so we make this explicit in the note
                cleanup_error.add_note(
                    f"Raised while tearing down dependency {_format_key(provider.key)}"
                    f" (scope={provider.scope!r}, provider={_describe_callable(provider.fn)})."
                )
                errors.append(cleanup_error)

        if not errors:
            if cancelled_error is not None:
                raise cancelled_error
            return
        failure: BaseException = (
            errors[0] if len(errors) == 1 else BaseExceptionGroup(f"{len(errors)} dependency cleanups failed", errors)
        )
        # failures take precedence over a cancellation, keeping behaviour in line with
        # asyncio.TaskGroup. whether it survives in the failure's context chain depends
        # on the stack it's bubbling up, so we add a note to make sure its source isn't
        # getting lost
        if cancelled_provider is not None:
            failure.add_note(
                "Takes precedence over cancellation delivered during the same teardown, "
                f"while tearing down dependency {_format_key(cancelled_provider.key)} "
                f"(scope={cancelled_provider.scope!r}, "
                f"provider={_describe_callable(cancelled_provider.fn)})."
            )
        elif isinstance(exc, asyncio.CancelledError):
            failure.add_note("Takes precedence over a cancellation of the cleanup task")
        task = asyncio.current_task()
        if _IS_PY_313_PLUS and task is not None and task.cancelling():
            # on 3.13+, a 'Task.uncancel()' that brings the cancel count to zero also
            # withdraws a cancellation that was requested but not yet delivered. before
            # 3.13 that cancellation is still delivered at the next await.
            #
            # we mimic 'TaskGroup's behaviour for errors occurring while a cancellation
            # request is outstanding: the cancellation is delivered at the next 'await'
            # instead of being lost with the exception, and the cancel count remains as
            # the canceller's own 'uncancel()' expects it. if the canceller consumes its
            # cancellation with that 'uncancel()' before the next await, the re-armed
            # cancellation is withdrawn with it from 3.13 onward. before 3.13 it would
            # be delivered *after* the canceller has completed, so there the
            # cancellation is dropped instead
            task.uncancel()
            task.cancel()
        raise failure


def _next_scope(registry: DIRegistry, scope: str) -> str:
    """Return the scope following ``scope``"""
    index = registry._scope_index[scope] + 1
    if index >= len(registry.scopes):
        raise DIScopeError(
            f"Scope {scope!r} is the innermost scope of registry {registry.name!r}. No "
            f"scopes follow it. scope order: {_format_scope_chain(registry.scopes)}"
        )
    return registry.scopes[index]
