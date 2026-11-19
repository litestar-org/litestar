# pyright: reportUnnecessaryTypeIgnoreComment=false
from __future__ import annotations

import asyncio
import contextlib
import contextvars
import enum
import functools
import inspect
from collections.abc import AsyncGenerator, AsyncIterable, AsyncIterator, Generator, Iterable, Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Annotated,
    Any,
    Final,
    Literal,
    TypeAlias,
    TypeVar,
    cast,
)

import anyio

from litestar.concurrency import get_asyncio_executor
from litestar.di._helpers import _bounded_repr, _describe_callable, _format_key
from litestar.di._request import RequestParameter, _request_dependency, _reserved_request_value_key
from litestar.di.exceptions import DIRegistrationError, DIResolutionError
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils.helpers import unwrap_partial
from litestar.utils.signature import ParsedSignature, get_fn_type_hints
from litestar.utils.typing import make_non_optional_union

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping
    from contextlib import AbstractAsyncContextManager, AbstractContextManager
    from types import TracebackType

    from litestar.di.context import _CleanupStack

__all__ = (
    "Dependency",
    "DependencyKey",
    "InjectionParameter",
    "InjectionTarget",
    "NamedDependency",
    "Provider",
    "ProviderKind",
    "TypeDependency",
    "provide",
)


T = TypeVar("T")


DependencyKey: TypeAlias = "str | type[Any]"

_DEFAULT_SCOPE: Final[str] = "handler"


class ProviderKind(enum.StrEnum):
    """Types of provider keys"""

    NAMED = "named"
    """Keyed by a name"""

    TYPE = "type"
    """Keyed by a type"""


def _get_provider_kind_for(
    key: DependencyKey | None,
    kind: Literal["named", "type"] | ProviderKind | None,
    *,
    subject: Callable[[], str],
) -> ProviderKind | None:
    """Return kind, derived from ``key`` and ``kind``.
    If 'kind' is given, it takes precedence. If 'key' is given as well, it must match
    'kind'. If 'kind' is not given, it will be inferred from 'key'.
    """
    try:
        explicit = ProviderKind(kind) if kind is not None else None
    except ValueError:
        known = ", ".join(repr(member.value) for member in ProviderKind)
        raise DIRegistrationError(f"{subject()}: Unknown kind {kind!r}, expected one of {known}") from None
    if key is None:
        return explicit
    derived = ProviderKind.NAMED if isinstance(key, str) else ProviderKind.TYPE
    if explicit is not None and explicit is not derived:
        msg = f"{subject()}: {'String' if derived is ProviderKind.NAMED else 'Type'} key does not match specified kind {explicit.value!r}"
        raise DIRegistrationError(msg)
    return derived


@dataclass(frozen=True, slots=True)
class Dependency:
    """Mark a parameter as a dependency.

    .. code-block:: python

        async def handler(
            session: Annotated[Session, Dependency("db_session")],
            replica: Annotated[Engine, Dependency(ReplicaEngine)],
        ) -> None: ...
    """

    key: DependencyKey | None = None
    """The key to resolve"""

    kind: Literal["named", "type"] | ProviderKind | None = None
    """Resolution strategy: by name or by type. If not given, inferred from 'key', or by name without a key"""

    def __post_init__(self) -> None:
        kind = _get_provider_kind_for(self.key, self.kind, subject=lambda: repr(self)) or ProviderKind.NAMED
        object.__setattr__(self, "kind", kind)

    @staticmethod
    def _get_from_field_definition(field: FieldDefinition) -> Dependency | None:
        """Extract the 'Dependency' marker from a 'FieldDefinition', if there is one.

        Raises:
            DIRegistrationError: If the metadata carries more than one marker.
        """
        marker: Dependency | None = field.get_from_metadata(cast("type[Any]", Dependency))
        if marker is not None and sum(isinstance(item, Dependency) for item in field.metadata) > 1:
            raise DIRegistrationError(f"Annotation {field.raw!r} carries more than one dependency marker")
        return marker


NamedDependency: TypeAlias = Annotated[T, Dependency(kind=ProviderKind.NAMED)]
"""Mark a parameter as a dependency resolved by *name*.

Equivalent to ``Annotated[T, Dependency(kind="named")]``
"""

TypeDependency: TypeAlias = Annotated[T, Dependency(kind=ProviderKind.TYPE)]
"""Mark a parameter as a dependency resolved by *type*.

Equivalent to ``Annotated[T, Dependency(kind="type")]``
"""


class _CallableForm(enum.Enum):
    ASYNC = enum.auto()
    SYNC = enum.auto()
    ASYNC_GENERATOR = enum.auto()
    GENERATOR = enum.auto()
    SEED = enum.auto()

    @classmethod
    def from_callable(cls, fn: Any) -> _CallableForm:
        target = unwrap_partial(fn)

        # A class constructs an instance: a plain sync factory. Checked before the ``__call__`` lookup,
        # because ``type(SomeClass).__call__`` is the metaclass's, not the class's.
        if isinstance(target, type):
            return cls.SYNC

        # A function is read as itself; a callable instance through the ``__call__`` on its type,
        # which is the one Python invokes. B004 wants ``callable()``, but ``inspect`` needs the
        # function object.
        call = target if inspect.isroutine(target) else getattr(type(target), "__call__", None)  # noqa: B004
        if inspect.isasyncgenfunction(call):
            return cls.ASYNC_GENERATOR
        if inspect.iscoroutinefunction(call):
            return cls.ASYNC
        if inspect.isgeneratorfunction(call):
            return cls.GENERATOR
        return cls.SYNC


@dataclass(frozen=True, slots=True)
class InjectionParameter:
    """A parameter of a provider or an injection target that DI fills."""

    parameter_name: str
    """Name of the parameter on the callable."""

    key: DependencyKey
    """Key of the dependency"""

    kind: ProviderKind
    """The provider kind"""

    optional: bool = False
    """Whether the parameter is optional (i.e. has a default)"""


def _copy_context_variables(source: contextvars.Context) -> None:
    """Set the context variables of ``source`` in the current context."""
    for var, value in source.items():
        if var.get(Empty) is not value:
            var.set(value)


async def _wait_until_done(future: asyncio.Future[Any]) -> asyncio.CancelledError | None:
    """Wait until ``future`` is done, also when the task waiting is cancelled. Return the first cancellation
    delivered during the wait.
    """
    try:
        await asyncio.wait([future])
    except asyncio.CancelledError as cancellation:
        # performance: anyio cancels a task of a cancelled cancel scope again at every
        # suspension point, resulting in a busy-loop, potentially saturating a CPU core.
        # https://github.com/agronholm/anyio/issues/884, https://github.com/agronholm/anyio/issues/1257
        # shielding the cancellation makes it work as expected: 'Task.cancel()' gets
        # through
        with anyio.CancelScope(shield=True):
            while not future.done():
                with contextlib.suppress(asyncio.CancelledError):
                    await asyncio.wait([future])
        return cancellation
    return None


class _SyncGeneratorContextManager:
    """An async context manager for a sync generator provider.

    The generator runs in threads, with a shared :class:`contextvars.Context`.
    """

    __slots__ = ("_context", "_context_manager")

    def __init__(self, context_manager_factory: Callable[..., AbstractContextManager[Any]], /, **kwargs: Any) -> None:
        self._context = contextvars.copy_context()
        self._context_manager = context_manager_factory(**kwargs)

    def _run_in_executor(
        self, executor: ThreadPoolExecutor | None, fn: Callable[..., T], *args: Any
    ) -> asyncio.Future[T]:
        call = functools.partial(self._context.run, fn, *args)
        return asyncio.get_running_loop().run_in_executor(executor, call)

    async def __aenter__(self) -> Any:
        entering = self._run_in_executor(get_asyncio_executor(), self._context_manager.__enter__)
        cancellation = await _wait_until_done(entering)
        if cancellation is None:
            value = entering.result()
            _copy_context_variables(self._context)
            return value
        if entering.exception() is None:
            await self._exit(type(cancellation), cancellation, cancellation.__traceback__)
        raise cancellation

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        self._context.run(_copy_context_variables, contextvars.copy_context())
        return await self._exit(exc_type, exc, traceback)

    async def _exit(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        # use a separate thread, because the threads from the executor may all be taken
        # until this code has run (by other generators waiting for what it releases,
        # e.g. a connection of a pool)
        executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="litestar-sync-generator-cleanup")
        exiting = self._run_in_executor(executor, self._context_manager.__exit__, exc_type, exc, traceback)
        executor.shutdown(wait=False)
        cancellation = await _wait_until_done(exiting)
        suppressed = exiting.result()
        if cancellation is not None:
            raise cancellation
        return suppressed


def _should_run_sync_in_thread(
    fn: Callable[..., Any], form: _CallableForm, sync_to_thread: bool | None, *, role: str, how: str
) -> bool:
    if form is not _CallableForm.SYNC:
        if sync_to_thread is not None:
            reason = "a sync generator function" if form is _CallableForm.GENERATOR else "not a synchronous callable"
            raise DIRegistrationError(f"sync_to_thread={sync_to_thread} has no effect on {fn} because it is {reason}")
        return False

    if sync_to_thread is not None:
        return sync_to_thread

    if isinstance(unwrap_partial(fn), type):
        # TODO: Mention in docs that DI into classes expects __init__ to never block
        return False

    # TODO: This would be a good place for a link to the docs
    raise DIRegistrationError(
        f"Missing 'sync_to_thread' on synchronous callable {fn}. A synchronous callable "
        "must declare whether it needs to run in a separate thread: An undeclared "
        "blocking call would otherwise block the event loop."
    )


def _dependency_marker_and_field_definition_from_field_definition(
    field: FieldDefinition,
) -> tuple[Dependency | None, FieldDefinition]:
    """Return the 'Dependency' marker on 'field' and the FieldDefinition it is on. Usually,
    these are the same, but for FieldDefinitions with inner types, the marker may be on
    an inner type, in which case the inner marked type is returned.
    """
    marker = Dependency._get_from_field_definition(field)
    marked = (
        [
            (member_marker, member)
            for member in field.inner_types
            if (member_marker := Dependency._get_from_field_definition(member)) is not None
        ]
        if field.is_union
        else []
    )
    if marker is not None and marked:
        raise DIRegistrationError(
            f"Annotation {field.raw!r} contains a dependency marker on the union as well "
            "as a member of it. A parameter may only declare one dependency"
        )
    if marker is not None:
        return marker, field
    if len(marked) > 1:
        raise DIRegistrationError(
            f"Annotation {field.raw!r} contains a dependency marker on more than one "
            f"member of the union. A parameter may only declare one dependency"
        )
    if marked:
        return marked[0]
    return None, field


def _dependency_key_for_marker(marker: Dependency, name: str, marked: FieldDefinition) -> DependencyKey:
    if marker.key is not None:
        return marker.key
    if marker.kind is ProviderKind.NAMED:
        return name
    # treat 'TypeDependency[T] | None' and 'TypeDependency[T | None]' as equivalent
    keyed = (
        FieldDefinition.from_annotation(make_non_optional_union(marked.annotation)) if marked.is_optional else marked
    )
    # a reserved request value is keyed as its implicit marker keys it
    return _reserved_request_value_key(keyed) or keyed.annotation


def _bound_keywords_of_partial(fn: Any) -> frozenset[str]:
    """Return the names of the parameters 'functools.partial' has bound, recursively"""
    # 'inspect.signature' shows a keyword-bound parameter as keyword-only with a
    # default, which would read as an optional dependency and be resolved over the
    # bound parameter of the partial
    bound: set[str] = set()
    while isinstance(fn, functools.partial):
        bound.update(fn.keywords)
        fn = fn.func
    return frozenset(bound)


def _parse_signature(fn: Any) -> ParsedSignature:
    target = unwrap_partial(fn)
    try:
        signature = inspect.signature(fn)
        hints = get_fn_type_hints(target)
        return ParsedSignature.from_signature(signature, hints)
    except Exception as exc:
        raise DIRegistrationError(f"Cannot inspect the signature of {_describe_callable(fn)}: {exc!r}") from exc


def _shape_given_signature_to_partial(fn: functools.partial[Any], signature: ParsedSignature) -> ParsedSignature:
    """Return ``signature`` with the parameters of the partial ``fn``: those it still takes, of the
    kinds it takes them as. ``signature`` may describe ``fn`` or the callable it wraps
    """
    try:
        shape = inspect.signature(fn)
    except Exception as exc:
        raise DIRegistrationError(f"Cannot inspect the signature of {_describe_callable(fn)}: {exc!r}") from exc
    return ParsedSignature(
        parameters={name: signature.parameters[name] for name in shape.parameters if name in signature.parameters},
        return_type=signature.return_type,
        original_signature=shape,
    )


def _marked_dependency(
    fn: Any, name: str, field: FieldDefinition
) -> tuple[ProviderKind, DependencyKey, RequestParameter | None] | None:
    """Return the kind and key of the dependency the parameter ``name`` is marked as, with
    its :class:`RequestParameter` if it has a parameter or body marker. ``None`` if it
    isn't marked
    """
    marker, marked = _dependency_marker_and_field_definition_from_field_definition(field)
    request_dependency = _request_dependency(fn, name, field)
    if marker is None:
        if request_dependency is None:
            return None
        key, request_parameter = request_dependency
        return ProviderKind.TYPE if request_parameter is None else ProviderKind.NAMED, key, request_parameter

    if request_dependency is not None and request_dependency[1] is not None:
        raise DIRegistrationError(
            f"Parameter {name!r} of {_describe_callable(fn)} is marked as a dependency "
            f"as well as a {type(field.kwarg_definition).__name__}. A parameter may "
            "only declare one dependency"
        )
    # Always a ProviderKind after ``__post_init__``
    return cast("ProviderKind", marker.kind), _dependency_key_for_marker(marker, name, marked), None


def _injection_parameters_from_fn(
    fn: Any, *, strict: bool, signature: ParsedSignature | None = None
) -> tuple[tuple[InjectionParameter, ...], tuple[str, ...], tuple[RequestParameter, ...], ParsedSignature]:
    """Extract a callable's parameters DI parameters.
    Return a tuple of 'InjectionParameter's, remaining parameters, the
    'RequestParameter's among the 'InjectionParameter's, and the callable's
    'ParsedSignature'.

    A parameter is a dependency if it has a dependency marker, a parameter or body
    marker, or a reserved request value annotation, which marks it implicitly (see
    :func:`_request_dependency`).

    Args:
        fn: The callable to inspect
        strict: Raise :class:`DIRegistrationError` for a parameter that is not marked as a
            dependency, and for ``*args`` and ``**kwargs``. 'True' for providers
        signature: The parsed signature of ``fn``, used instead of reading it from ``fn``. For a
            :func:`functools.partial`, it may be that of the callable it wraps
    """
    if signature is None:
        parsed = _parse_signature(fn)
    elif isinstance(fn, functools.partial):
        parsed = _shape_given_signature_to_partial(fn, signature)
    else:
        parsed = signature
    dependencies: list[InjectionParameter] = []
    parameters: list[str] = []
    request_parameters: list[RequestParameter] = []
    bound_by_partial = _bound_keywords_of_partial(fn)

    for name, field in parsed.parameters.items():
        parameter_kind = parsed.original_signature.parameters[name].kind
        if parameter_kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD):
            variadic = "*" if parameter_kind is inspect.Parameter.VAR_POSITIONAL else "**"
            if strict:
                raise DIRegistrationError(
                    f"Provider {_describe_callable(fn)} declares {variadic}{name}. A provider is only ever called with "
                    f"its resolved dependencies, so a variadic parameter can never receive anything. Remove {variadic}{name}."
                )
            if _marked_dependency(fn, name, field) is not None:
                raise DIRegistrationError(
                    f"Parameter {variadic + name!r} of {_describe_callable(fn)} is marked as a dependency but is "
                    "variadic, so it could never be filled"
                )
            continue  # a target's unmarked variadics are the caller's

        if name in bound_by_partial:
            parameters.append(name)
            continue

        marked_dependency = _marked_dependency(fn, name, field)
        if marked_dependency is None:
            if strict:
                raise DIRegistrationError(
                    f"Parameter {name!r} of provider {_describe_callable(fn)} is not marked as a dependency. "
                    f"Mark it, e.g. as '{name}: NamedDependency[...]', '{name}: TypeDependency[...]' "
                    f"or '{name}: FromQuery[...]'"
                )
            parameters.append(name)
            continue
        kind, key, request_parameter = marked_dependency

        if parameter_kind is inspect.Parameter.POSITIONAL_ONLY:
            raise DIRegistrationError(
                f"Parameter {name!r} of {_describe_callable(fn)} is marked as a dependency but is "
                "a positional-only parameter. Dependencies are always passed as keyword arguments, "
                "so it could never be filled"
            )

        if request_parameter is not None:
            request_parameters.append(request_parameter)
        dependencies.append(
            InjectionParameter(
                parameter_name=name,
                key=key,
                kind=kind,
                optional=field.has_default,
            )
        )

    return tuple(dependencies), tuple(parameters), tuple(request_parameters), parsed


class Provider:
    """A factory to produce a value"""

    def __init__(
        self,
        fn: Callable[..., Any] | None,
        kind: Literal["named", "type"] | ProviderKind | None = None,
        scope: str = _DEFAULT_SCOPE,
        key: DependencyKey | None = None,
        sync_to_thread: bool | None = None,
        signature: ParsedSignature | None = None,
    ) -> None:
        """DI provider. A factory to produce a value.

        A factory callable may be:

        - an async callable
        - a sync callable: In this case, sync_to_thread must be passed explicitly, to define
          how it should be invoked. Blocking synchronous callables should pass sync_to_thread=True,
          so they can run in a thread pool without blocking the main event loop.
          See :doc:`/topics/sync-vs-async` for more info.
          A class is treated as a non-blocking sync callable. It's __init__ and __new__ methods should
          *never* block
        - an async generator, yielding exactly once. The yielded value is the factory value.
          the code after the ``yield`` will be invoked as a cleanup step when this provider's DIContext
          closes. If the context is closing with an active exception, that exception will be thrown into
          the generator. Cleanups are guaranteed to run in reverse order they providers were invoked in.
          Every cleanup will be invoked, even if prior cleanups raised an exception. Exceptions during
          cleanup steps are re-raised once all cleanups have completed.
        - a sync generator, yielding exactly once, with the cleanup step of an async generator. The code
          up to the ``yield`` runs in a worker thread, the cleanup step in a thread of its own, both in
          one :class:`contextvars.Context`: a context variable set before the ``yield`` is set after it,
          and set for whoever resolves the provider. A context variable set where the context closes is
          set for the cleanup step

        A provider may declare no 'fn', which makes it a *seed*. Seeds are expected to be given values for their
        context explicitly when that context is created. The shorthand for this is :meth:`Provider.seed()`

        Args:
            fn: The factory callable, or ``None`` to declare a seed, whose value is given to the
                context owning its scope when it is built
            kind: Whether this provider is keyed by name or by type
            scope: Name of the lifetime-scope where the produced value is stored
            key: The key to register under. If omitted it is inferred: from ``fn.__name__`` for
                a named provider, and from the return annotation (or the class itself) for
                a type provider
            sync_to_thread: Whether a sync callable runs in a worker thread
            signature: The parsed signature of ``fn``, used instead of reading it from ``fn``. For
                a :func:`functools.partial`, it may be that of the callable it wraps

        Raises:
            DIRegistrationError: If ``fn`` is not a supported callable, ``key`` contradicts
                ``kind``, a seed is declared without a key or with a signature, or
                ``sync_to_thread`` contradicts the callable's form.
        """
        if isinstance(fn, Provider):
            raise DIRegistrationError(f"{fn!r} is already a Provider")

        def subject() -> str:
            # For messages only: describing a callable reads its source.
            return _describe_callable(fn) if fn is not None else f"seed {_format_key(key)}"

        self.kind = _get_provider_kind_for(key, kind, subject=lambda: f"Provider {subject()}") or ProviderKind.NAMED
        self.fn = fn
        self.scope = scope
        self._explicit_key = key
        self._signature = signature
        self._resolved = False
        self._context_manager_factory: Callable[..., AbstractAsyncContextManager[Any]] | None = None

        if fn is None:
            # it's a seed

            if key is None:
                raise DIRegistrationError(
                    "Missing key for provider without factory. Providers without a factory callable are "
                    "considered seed values, and require a key. Declare it as Provider.seed(<key>)"
                )
            if signature is not None:
                raise DIRegistrationError(
                    f"Provider {subject()} is given a signature, but has no factory callable it could describe"
                )
            self._form = _CallableForm.SEED
            self.sync_to_thread = False
            self.dependencies = ()
            self.non_di_parameters = ()
            self.request_parameters = ()
            self._resolved = True
            return

        self._form = _CallableForm.from_callable(fn)
        self.sync_to_thread = _should_run_sync_in_thread(
            fn,
            self._form,
            sync_to_thread,
            role="Provider",
            how="on the provider",
        )
        if self._form is _CallableForm.ASYNC_GENERATOR:
            self._context_manager_factory = contextlib.asynccontextmanager(fn)
        elif self._form is _CallableForm.GENERATOR:
            self._context_manager_factory = functools.partial(
                _SyncGeneratorContextManager, contextlib.contextmanager(fn)
            )

        self._update_wrapper(fn)

    def _update_wrapper(self, fn: Callable[..., Any]) -> None:
        functools.update_wrapper(self, fn, updated=())
        with contextlib.suppress(AttributeError):
            if self._form is _CallableForm.ASYNC:
                inspect.markcoroutinefunction(self)  # type: ignore [attr-defined]

    @classmethod
    def seed(cls, key: DependencyKey, scope: str = _DEFAULT_SCOPE) -> Provider:
        """Create a provider without a factory. Its value must be passed to the DIContext explicitly at creation time.

        The kind is inferred from the key. A string key creates a name dependency, anything
        else a type dependency.
        """
        return cls(None, scope=scope, key=key)

    @functools.cached_property
    def key(self) -> DependencyKey:
        """Key this provider is registered under"""
        return self._explicit_key if self._explicit_key is not None else self._infer_key()

    # 'resolve_signature' sets the next three
    @functools.cached_property
    def dependencies(self) -> tuple[InjectionParameter, ...]:
        """Sub-dependencies of this provider"""
        self.resolve_signature()
        return self.dependencies

    @functools.cached_property
    def non_di_parameters(self) -> tuple[str, ...]:
        """Names of the factory callable's parameters that a :func:`functools.partial` binds by keyword"""
        self.resolve_signature()
        return self.non_di_parameters

    @functools.cached_property
    def request_parameters(self) -> tuple[RequestParameter, ...]:
        """Sub-dependencies of this provider that carry a parameter or body marker"""
        self.resolve_signature()
        return self.request_parameters

    @functools.cached_property
    def is_seed(self) -> bool:
        """Whether this provider is a seed"""
        return self._form is _CallableForm.SEED

    def resolve_signature(self, signature: ParsedSignature | None = None) -> None:
        """Extract sub-dependencies and the remaining parameters from the provider callable's
        signature. ``signature`` is read instead of the callable's when the provider was given
        none at construction.
        """
        if self._resolved:
            return

        signature = self._signature if self._signature is not None else signature
        self.dependencies, self.non_di_parameters, self.request_parameters, _ = _injection_parameters_from_fn(
            self.fn, strict=True, signature=signature
        )
        self._signature = signature
        self._resolved = True

    def _infer_key(self) -> DependencyKey:
        """Infer the key for a provider.
        For a named dependency, the callable's name, for a type dependency, the
        callable's return/yield type, or the type itself if a class is used as a provider
        directly.
        """
        target = unwrap_partial(self.fn)

        if self.kind is ProviderKind.NAMED:
            name = getattr(target, "__name__", None)
            if not name:
                raise DIRegistrationError(
                    f"Cannot infer a name key for {_describe_callable(self.fn)}: it has no"
                    " '__name__'."
                    "\n  Pass an explicit key, e.g. provide(key='my_dependency')."
                )
            return name  # type: ignore[no-any-return]

        # a class is registered by type is its own key
        if isinstance(target, type):
            return target

        field = (self._signature if self._signature is not None else _parse_signature(self.fn)).return_type
        if field.annotation is Empty:
            raise DIRegistrationError(
                f"Cannot infer a type key for {_describe_callable(self.fn)}: it has no return "
                "annotation. Annotate the return type, or pass an explicit key, e.g. "
                "'provide(kind='type', key=Database)."
            )

        if self._form in (_CallableForm.ASYNC_GENERATOR, _CallableForm.GENERATOR):
            is_async = self._form is _CallableForm.ASYNC_GENERATOR
            origins = (AsyncGenerator, AsyncIterator, AsyncIterable) if is_async else (Generator, Iterator, Iterable)
            if field.origin not in origins or not field.inner_types:
                raise DIRegistrationError(
                    f"Cannot infer a type key for {'async' if is_async else 'sync'} generator provider "
                    f"{_describe_callable(self.fn)}: "
                    f"Missing type parameter for its return annotation {field.raw!r} ."
                    "Supply the generic parameter or define a key explicitly"
                )
            field = field.inner_types[0]

        if field.is_builtin_constant_type:
            # builtin constants are not allowed
            raise DIRegistrationError(
                f"Cannot infer a type key for {_describe_callable(self.fn)} with constant return annotation '{field.annotation!r}'"
            )
        if field.is_union:
            raise DIRegistrationError(
                f"Cannot infer a type key for {_describe_callable(self.fn)} with union return annotation: "
                f"{field.annotation!r}. A provider can only provide one key. Change the return annotation to "
                f"a single type, or provide a key explicitly, e.g. provide(kind='type', key=T)."
            )

        return field.annotation  # type: ignore[no-any-return]

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call underlying factory as-is"""
        return self._factory()(*args, **kwargs)

    def __repr__(self) -> str:
        name = type(self).__name__
        if self._form is _CallableForm.SEED:
            return f"{name}.seed({self._explicit_key!r}, scope={self.scope!r})"
        arguments = [_bounded_repr.repr(self.fn), f"kind={self.kind.value!r}", f"scope={self.scope!r}"]
        # An inferred key is shown once read, which a repr does not trigger.
        key = vars(self).get("key", self._explicit_key)
        if key is not None:
            arguments.append(f"key={key!r}")
        if self._form is _CallableForm.SYNC:
            arguments.append(f"sync_to_thread={self.sync_to_thread!r}")
        return f"{name}({', '.join(arguments)})"

    def _factory(self) -> Callable[..., Any]:
        """Return the factory callable

        Raises:
            DIResolutionError: If this provider is a seed: there is no factory to run.
        """
        if self.fn is None:
            raise DIResolutionError(f"Dependency {_format_key(self.key)} is declared as a seed and has no callable")
        return self.fn

    async def _produce(self, kwargs: Mapping[str, Any], stack: _CleanupStack | None) -> Any:
        """Produce a value from the factory, with ``kwargs`` as its resolved dependencies.

        A generator provider is entered on ``stack``, which it requires
        """
        fn = self._factory()
        if self._context_manager_factory is not None:
            return await stack.enter_async_context(self._context_manager_factory(**kwargs), self)  # type: ignore[union-attr]
        if self._form is _CallableForm.ASYNC:
            return await fn(**kwargs)
        if self.sync_to_thread:
            return await asyncio.to_thread(fn, **kwargs)
        return fn(**kwargs)


def provide(
    scope: str = _DEFAULT_SCOPE,
    kind: Literal["named", "type"] | ProviderKind | None = None,
    key: DependencyKey | None = None,
    sync_to_thread: bool | None = None,
) -> Callable[[Callable[..., Any]], Provider]:
    """A decorator wrapping the callable into a :class:`Provider`.

    Args:
        scope: Name of the scope owning the produced value.
        kind: Whether the provider is keyed by name or by type. If not given, inferred
            from ``key``, or by name without a key
        key: Key this factory provides for. If not given, will be inferred. From the
        callable's name for ``kind="named"`` (the default), and from the callable's
        return type for ``kind="type"``
        sync_to_thread: Whether a sync callable runs in a worker thread; see :class:`Provider`
            for more information

    Raises:
        DIRegistrationError: If used as a bare ``@provide`` without parentheses.

    """

    def decorator(fn: Callable[..., Any]) -> Provider:
        return Provider(fn, kind=kind, scope=scope, key=key, sync_to_thread=sync_to_thread)

    return decorator


class InjectionTarget:
    """A callable whose dependencies are read from its signature, for :meth:`DIContext.inject`,
    :meth:`DIContext.solve_arguments` and :meth:`DIRegistry.check_target`.

    It has the same calling semantics as a :class:`Provider`, but does not provide a
    value into the context.
    """

    def __init__(self, fn: Callable[..., Any], signature: ParsedSignature | None = None) -> None:
        """Wrap ``fn`` as an injection target.

        Args:
            fn: The callable to call with its dependencies resolved
            signature: The parsed signature of ``fn``, used instead of reading it from ``fn``. For
                a :func:`functools.partial`, it may be that of the callable it wraps
        """
        if isinstance(fn, InjectionTarget):
            raise DIRegistrationError(f"{fn!r} is already an InjectionTarget.")
        if isinstance(fn, Provider):
            raise DIRegistrationError(
                f"{fn!r} is a Provider, not an injection target."
                "\n  A provider's value is produced once per scope and cached; injecting into it"
                "\n  would build a second one, with its own teardown, outside the context that"
                "\n  owns it."
                f"\n  Resolve it instead: 'await context.solve({fn.key!r})'."
            )
        self._fn = fn
        self.dependencies, _, self.request_parameters, parsed = _injection_parameters_from_fn(
            fn, strict=False, signature=signature
        )
        parameters = parsed.original_signature.parameters.values()
        # TODO: Move this to ParsedSignature
        self._positional_names = tuple(
            p.name
            for p in parameters
            if p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)
        )
        self._parameter_names = frozenset(
            p.name
            for p in parameters
            if p.kind not in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
        )
        self._takes_any_keyword = any(p.kind is inspect.Parameter.VAR_KEYWORD for p in parameters)
        self._form = _CallableForm.from_callable(fn)
        functools.update_wrapper(self, fn, updated=())
        mark_coroutine_function = getattr(inspect, "markcoroutinefunction", None)
        if mark_coroutine_function is not None and self._form is _CallableForm.ASYNC:
            mark_coroutine_function(self)

    def __repr__(self) -> str:
        return f"{type(self).__name__}({_bounded_repr.repr(self._fn)})"

    @property
    def fn(self) -> Callable[..., Any]:
        """The wrapped callable"""
        return self._fn

    def __call__(self, *args: Any, **kwargs: Any) -> Any:
        """Call the callable as-is"""
        return self._fn(*args, **kwargs)

    async def _call(self, args: tuple[Any, ...], kwargs: dict[str, Any], *, sync_to_thread: bool | None) -> Any:
        """Call the target with 'kwargs' as resolved dependencies"""
        offload = _should_run_sync_in_thread(
            self._fn, self._form, sync_to_thread, role="Injection target", how="on the call to inject"
        )
        if self._form is _CallableForm.ASYNC:
            return await self._fn(*args, **kwargs)
        if offload:
            return await asyncio.to_thread(self._fn, *args, **kwargs)
        return self._fn(*args, **kwargs)

    @staticmethod
    def _for_callable(fn: Callable[..., Any]) -> InjectionTarget:
        """Return the InjectionTarget for ``fn``.

        If 'fn' is an InjectionTarget, it is returned unchanged.
        If 'fn' is a callable, an 'InjectionTarget' will be created for it, and attempted
        to store as a function attribute. If caching is successful, subsequent calls
        to this method will return the same 'InjectionTarget' for that callable,
        """
        if isinstance(fn, InjectionTarget):
            return fn
        kept = getattr(fn, _INJECTION_TARGET_FN_CACHE_ATTRIBUTE, None)
        if isinstance(kept, InjectionTarget) and kept._fn is fn:
            return kept
        target = InjectionTarget(fn)
        with contextlib.suppress(AttributeError, TypeError):  # a callable that cannot hold an attribute
            setattr(fn, _INJECTION_TARGET_FN_CACHE_ATTRIBUTE, target)
        return target


_INJECTION_TARGET_FN_CACHE_ATTRIBUTE = "__litestar_injection_target__"
"""Where :meth:`InjectionTarget._for_callable` keeps the target it built for a bare callable."""
