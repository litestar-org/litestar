from __future__ import annotations

import contextlib
import warnings
from dataclasses import dataclass, replace
from inspect import isclass
from typing import TYPE_CHECKING, Any, Final

from litestar._request_parameters.declarations import (
    RequestParameterDefinition,
    apply_layer_parameters,
    merge_request_parameters,
)
from litestar.connection import WebSocket
from litestar.datastructures import Headers, ImmutableState
from litestar.di._helpers import _describe_provider, _format_key
from litestar.di._provide import Provide
from litestar.di.context import PreparedDIContext
from litestar.di.exceptions import DIRegistrationError, MissingProviderError
from litestar.di.provider import InjectionTarget, Provider, _CallableForm, _marked_dependency
from litestar.di.registry import DIRegistry
from litestar.exceptions import DTOFactoryException, ImproperlyConfiguredException, LitestarDeprecationWarning
from litestar.params import QueryParams, RawBody, RequestCookies
from litestar.routes.base import BaseRoute
from litestar.types import Scope
from litestar.utils.helpers import unwrap_partial
from litestar.utils.signature import ParsedSignature
from litestar.utils.warnings import warn_implicit_sync_to_thread

if TYPE_CHECKING:
    from collections.abc import Callable, Generator, Iterable, Mapping

    from litestar.app import Litestar
    from litestar.connection import ASGIConnection
    from litestar.di.provider import DependencyKey
    from litestar.handlers import BaseRouteHandler
    from litestar.plugins import PluginRegistry
    from litestar.types import AnyCallable
    from litestar.typing import FieldDefinition

__all__ = ("HandlerInjectionSetup", "ProvideConverter", "create_handler_injection_setup")


@dataclass(frozen=True, slots=True)
class HandlerInjectionSetup:
    """What injecting a handler's function takes"""

    target: InjectionTarget
    """The handler's function as an injection target"""

    registry: DIRegistry
    """The frozen registry of the handler's providers"""

    request_context: PreparedDIContext
    """Creates the context of a request: of the registry, nested in the app's context if the app has one"""

    handler_context: PreparedDIContext
    """Creates the context of a call of the handler's function: of the registry, nested in the request's context"""

    request_parameter_definitions: dict[str, RequestParameterDefinition]
    """The request parameters of the handler's function, providers and layers, by key, each merged
    from its declarations
    """

    connection_seed_keys: tuple[DependencyKey, ...]
    """The keys the registry seeds the handler's connection under: its class and each class it inherits
    from up to :class:`~litestar.connection.ASGIConnection`
    """

    fn_seed_parameters: tuple[tuple[str, DependencyKey], ...]
    """The parameters of the handler's function that take a seed of the handler context, the
    connection or a request parameter, each as its name and the seed's key
    """

    fn_has_dependencies_to_resolve: bool
    """Whether the handler's function has a dependency that is no seed of the handler context"""


class ProvideConverter:
    """Convert the declarations of a handler's ``dependencies`` to providers"""

    __slots__ = ("_plugins", "_providers")

    def __init__(self, plugins: PluginRegistry) -> None:
        """Create a converter, reading the signature of a class a DI plugin supports from that plugin.

        Args:
            plugins: The app's plugins
        """
        self._plugins = plugins
        # keyed by the declaration's id, because a callable need not be hashable. the declaration
        # is kept alive along with its provider, so its id is not reused
        self._providers: dict[tuple[int, DependencyKey], tuple[Provide | AnyCallable, Provider]] = {}

    def convert(self, declaration: Provider | Provide | AnyCallable, key: DependencyKey) -> Provider:
        """Return the provider for ``declaration`` declared under ``key``: a ``Provider`` itself,
        otherwise the same object for every call with the same declaration and key. Its signature
        is resolved, for a class a DI plugin supports from that plugin's description.

        A ``Provide`` becomes a provider with scope ``"app"`` with ``use_cache=True``, ``"handler"``
        otherwise, and its ``sync_to_thread``. A callable becomes a provider with scope
        ``"handler"``; a synchronous one that is not a class runs on the event loop, warning that
        it has no ``sync_to_thread``.

        Raises:
            DIRegistrationError: If a ``Provider``'s key is not ``key``, the provider cannot be
                created from the declaration, e.g. for a ``Provide`` of a synchronous callable
                without ``sync_to_thread``, or its signature cannot be read.
        """
        if isinstance(declaration, Provider):
            if declaration.key != key:
                raise DIRegistrationError(
                    f"Provider {_describe_provider(declaration)} has the key {_format_key(declaration.key)}, "
                    f"but is declared under the key {_format_key(key)}"
                )
            self._resolve_signature(declaration)
            return declaration

        cache_key = (id(declaration), key)
        if (cached := self._providers.get(cache_key)) is not None:
            return cached[1]

        fn: Callable[..., Any]
        if isinstance(declaration, Provide):
            fn = declaration.dependency
            scope = "app" if declaration.use_cache else "handler"
            sync_to_thread = declaration.sync_to_thread
        else:
            fn = declaration
            scope = "handler"
            sync_to_thread = None
            if _CallableForm.from_callable(fn) is _CallableForm.SYNC and not isclass(unwrap_partial(fn)):
                warn_implicit_sync_to_thread(fn)
                sync_to_thread = False
        provider = Provider(fn, key=key, scope=scope, sync_to_thread=sync_to_thread)
        self._resolve_signature(provider)
        self._providers[cache_key] = (declaration, provider)
        return provider

    def _resolve_signature(self, provider: Provider) -> None:
        if provider._resolved:
            return
        target = unwrap_partial(provider.fn)
        plugin = next((plugin for plugin in self._plugins.di if plugin.has_typed_init(target)), None)
        provider.resolve_signature(ParsedSignature.from_signature(*plugin.get_typed_init(target)) if plugin else None)


@dataclass
class HandlerErrorPrefix:
    handler: str
    paths: list[str]
    dependencies: tuple[DependencyKey, ...] = ()

    @classmethod
    def for_handler(cls, handler: BaseRouteHandler) -> HandlerErrorPrefix:
        """Return the prefix naming ``handler`` by its ``name`` option, or its function's name, and its paths."""
        return cls(handler=handler.name or handler.handler_name, paths=sorted(handler.paths))

    def format(self, msg: str | None = None) -> str:
        paths = ",".join(sorted(self.paths))
        out = f"[paths={paths!r}, handler={self.handler!r}"
        if self.dependencies:
            out += f", dependencies={' -> '.join(_format_key(key) for key in reversed(self.dependencies))}"
        out += "]"
        if msg:
            out = f"{out} {msg}"
        return out

    @contextlib.contextmanager
    def wrap_config_exception(self) -> Generator[None]:
        try:
            yield
        except ImproperlyConfiguredException as exc:
            new_msg = self.format(exc.detail)
            raise ImproperlyConfiguredException(new_msg) from exc
        except DIRegistrationError as exc:
            raise DIRegistrationError(self.format(str(exc))) from exc

    @contextlib.contextmanager
    def wrap_dto_exception(self) -> Generator[None]:
        """Prefix the message of a :class:`~litestar.exceptions.DTOFactoryException` raised in the block and re-raise
        the same exception, keeping its class, attributes and traceback.
        """
        try:
            yield
        except DTOFactoryException as exc:
            detail = exc.detail
            if not detail:
                exc.detail = self.format()
                raise
            prefixed = self.format(detail)
            exc.detail = prefixed
            exc.args = tuple(arg.replace(detail, prefixed, 1) if isinstance(arg, str) else arg for arg in exc.args)
            raise


def _has_handler_scope(declaration: Provider | Provide | AnyCallable) -> bool:
    if isinstance(declaration, Provider):
        return declaration.scope == "handler"
    return not (isinstance(declaration, Provide) and declaration.use_cache)


def _create_fn_injection_target(handler: BaseRouteHandler) -> InjectionTarget:
    signature = apply_layer_parameters(handler.parsed_fn_signature, handler.parameter_field_definitions)
    target = InjectionTarget(handler.fn, signature=signature)
    declared = {dependency.parameter_name for dependency in target.dependencies}
    for name, field in signature.parameters.items():
        # a parameter a partial binds is no dependency of the target, marked or not
        if name not in declared and _marked_dependency(handler.fn, name, field) is None:
            raise ImproperlyConfiguredException(f"Missing declaration for parameter {name!r}")
    return target


def _apply_layer_parameters_to_provider(
    provider: Provider, layer_parameters: Mapping[str, FieldDefinition]
) -> Provider:
    """Return ``provider`` if none of its parameters binds one of ``layer_parameters``, otherwise a
    provider of the same callable, kind, key, scope and ``sync_to_thread`` whose parameters that
    bind a layer parameter carry that layer parameter's declaration, see
    :func:`~litestar._request_parameters.declarations.apply_layer_parameters`.
    """
    signature = provider._signature
    if signature is None:  # a seed
        return provider
    applied = apply_layer_parameters(signature, layer_parameters)
    if applied is signature:
        return provider
    return type(provider)(
        provider.fn,
        kind=provider.kind,
        scope=provider.scope,
        key=provider.key,
        sync_to_thread=provider.sync_to_thread if provider._form is _CallableForm.SYNC else None,
        signature=applied,
    )


def _dependency_keys(target: InjectionTarget, providers: Iterable[Provider]) -> set[DependencyKey]:
    return {
        dependency.key
        for dependencies in (target.dependencies, *(provider.dependencies for provider in providers))
        for dependency in dependencies
    }


def _check_body_not_declared(
    callables: Iterable[tuple[str, InjectionTarget | Provider]], connection_class: type[ASGIConnection]
) -> None:
    """Raise if one of ``callables``, those of a handler taking no body, declares the body.

    Args:
        callables: The handler's function and providers, each with a description used in error messages
        connection_class: The class of the handler's connection

    Raises:
        ImproperlyConfiguredException: If a parameter declares the body or the raw body.
    """
    handler_kind = (
        "a websocket handler" if issubclass(connection_class, WebSocket) else "a handler whose methods include 'GET'"
    )
    for owner, callable_ in callables:
        body_parameter_names = {
            parameter.parameter_name for parameter in callable_.request_parameters if parameter.is_body
        }
        for dependency in callable_.dependencies:
            if dependency.key is RawBody or dependency.parameter_name in body_parameter_names:
                body = "the raw request body" if dependency.key is RawBody else "the request body"
                raise ImproperlyConfiguredException(
                    f"Parameter {dependency.parameter_name!r} of {owner} declares {body}, which {handler_kind} "
                    "does not take"
                )


_DEPRECATED_REQUEST_VALUES: Final[dict[Any, tuple[str, str]]] = {
    Headers: ("Headers", "headers"),
    QueryParams: ("QueryParams", "query_params"),
    RequestCookies: ("RequestCookies", "cookies"),
    Scope: ("Scope", "scope"),
}


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else f"{', '.join(items[:-1])} and {items[-1]}"


def _warn_deprecated_request_values(
    callable_: InjectionTarget | Provider, prefix: HandlerErrorPrefix, *, connection: str | None
) -> None:
    deprecated = [
        (dependency.parameter_name, *_DEPRECATED_REQUEST_VALUES[dependency.key])
        for dependency in callable_.dependencies
        if dependency.key in _DEPRECATED_REQUEST_VALUES
    ]
    if not deprecated:
        return
    names = _join([repr(name) for name, _, _ in deprecated])
    types = _join([repr(type_name) for _, type_name, _ in deprecated])
    attributes = _join([repr(f"{connection or 'connection'}.{attribute}") for _, _, attribute in deprecated])
    if len(deprecated) == 1:
        message = f"Parameter {names} declares {types}, which is deprecated. Use {attributes}"
    else:
        message = f"Parameters {names} declare {types}, which are deprecated. Use {attributes}"
    if connection is None:
        message += " with 'connection: ASGIConnection'"
    warnings.warn(prefix.format(f"{message} instead"), LitestarDeprecationWarning, stacklevel=2)


def create_handler_injection_setup(
    handler: BaseRouteHandler,
    app: Litestar,
    *,
    connection_class: type[ASGIConnection],
    accepts_body: bool,
) -> HandlerInjectionSetup:
    """Return what injecting ``handler``'s function takes.

    A parameter of the function or of a provider with a bare marker named like a layer parameter
    declares that layer parameter, see
    :func:`~litestar._request_parameters.declarations.apply_layer_parameters`.

    The registry holds the app's seeds, the seeds of ``connection_class``, the providers of the
    reserved request values and of the state classes the providers and the function depend on,
    a seed for each request parameter of the function, the providers and the layers, and these
    providers of ``handler.dependencies``:
    the ones the function reaches (those its dependencies name, and the ones these name in
    turn), and the ones of every scope but ``"handler"`` with the ones they name in turn. A
    provider with a parameter declaring a layer parameter is held as a provider of its own for
    this handler, of the same callable, kind, key, scope and ``sync_to_thread``.

    Args:
        handler: A registered handler
        app: The app the handler is registered with
        connection_class: The class of the handler's connection
        accepts_body: Whether the handler takes the request body

    Raises:
        ImproperlyConfiguredException: If a parameter of the function declares no dependency,
            the declarations of a request parameter differ, a required path parameter is missing
            from one of the handler's paths, or without ``accepts_body`` the function or a
            provider declares the body.
        DIException: If the function's signature cannot be read, a provider cannot be
            registered, the registry's graph is invalid, the function depends on a key
            without a provider, or a context of the registry cannot be nested in the app's
            context.
    """
    prefix = HandlerErrorPrefix.for_handler(handler)
    with prefix.wrap_config_exception():
        target = _create_fn_injection_target(handler)
    reached: dict[DependencyKey, Provider] = {}

    def reach(keys: Iterable[DependencyKey]) -> None:
        # the chain of keys each pending key is reached through, the key itself last
        pending: list[tuple[DependencyKey, ...]] = [(key,) for key in keys]
        while pending:
            chain = pending.pop()
            key = chain[-1]
            if key in reached or key not in handler.dependencies:
                continue
            with replace(prefix, dependencies=chain).wrap_config_exception():
                reached[key] = provider = _apply_layer_parameters_to_provider(
                    app._provide_converter.convert(handler.dependencies[key], key), handler.parameter_field_definitions
                )
            pending.extend((*chain, dependency.key) for dependency in provider.dependencies)

    # the layer providers the function uses: those its dependencies name, and the ones these name in turn. then
    # those of every scope but 'handler', used or not: they can be resolved through the request's context
    reach(dependency.key for dependency in target.dependencies)
    used = set(reached)
    reach(key for key, declaration in handler.dependencies.items() if not _has_handler_scope(declaration))
    user_providers = [reached[key] for key in handler.dependencies if key in reached]
    callables: list[tuple[str, InjectionTarget | Provider]] = [
        (f"handler {prefix.handler!r}", target),
        *((f"provider {_format_key(provider.key)}", provider) for provider in user_providers),
    ]
    with prefix.wrap_config_exception():
        if not accepts_body:
            _check_body_not_declared(callables, connection_class)
        definitions = merge_request_parameters(
            {owner: callable_.request_parameters for owner, callable_ in callables},
            layer_parameters=handler.parameter_field_definitions,
            paths={path: BaseRoute._parse_path(path)[3].keys() for path in handler.paths},
        )

    provider_factory = app._builtin_provider_factory
    app_registry = app.dependency_registry
    connection_seeds = provider_factory.connection_seeds(connection_class)
    providers = [
        *(provider_factory.app_seeds if app_registry is not None else ()),
        *connection_seeds,
        *provider_factory.request_value_providers(accepts_body=accepts_body),
        *(Provider.seed(key, scope="handler") for key in definitions),
        *user_providers,
    ]
    state_providers = [
        provider_factory.state_provider(key)
        for key in _dependency_keys(target, providers)
        if isinstance(key, type) and issubclass(key, ImmutableState)
    ]
    registry = DIRegistry(prefix.format(), [*state_providers, *providers], scopes=app._dependency_scopes)
    try:
        registry.freeze()
    except MissingProviderError as exc:
        if len(exc.path) > 1 and (key := exc.path[-2]) not in used:
            kept_scopes = " and ".join(repr(scope) for scope in registry.scopes if scope != "handler")
            exc.add_note(
                f"Handler {prefix.handler!r} does not use {_format_key(key)}. Its registry holds the providers of scope "
                f"{kept_scopes} of its layers and what they depend on"
            )
        raise
    registry.check_target(target)
    _warn_deprecated_request_values(
        target, prefix, connection="socket" if issubclass(connection_class, WebSocket) else "request"
    )
    for provider in user_providers:
        _warn_deprecated_request_values(provider, replace(prefix, dependencies=(provider.key,)), connection=None)
    request_context = PreparedDIContext(
        registry, parent=PreparedDIContext(app_registry) if app_registry is not None else None
    )
    handler_context = PreparedDIContext(registry, parent=request_context)
    connection_seed_keys = tuple(seed.key for seed in connection_seeds)
    fn_seed_parameters = tuple(
        (dependency.parameter_name, dependency.key)
        for dependency in target.dependencies
        if dependency.key in connection_seed_keys or dependency.key in definitions
    )
    return HandlerInjectionSetup(
        target=target,
        registry=registry,
        request_context=request_context,
        handler_context=handler_context,
        request_parameter_definitions=definitions,
        connection_seed_keys=connection_seed_keys,
        fn_seed_parameters=fn_seed_parameters,
        fn_has_dependencies_to_resolve=len(target.dependencies) > len(fn_seed_parameters),
    )
