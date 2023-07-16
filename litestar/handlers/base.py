from __future__ import annotations

from copy import copy
from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Mapping, Sequence, cast

from litestar._signature import SignatureModel
from litestar.di import Provide
from litestar.dto.interface import HandlerContext
from litestar.exceptions import ImproperlyConfiguredException
from litestar.serialization import default_deserializer
from litestar.types import (
    Dependencies,
    Empty,
    ExceptionHandlersMap,
    Guard,
    MaybePartial,
    Middleware,
    TypeDecodersSequence,
    TypeEncodersMap,
)
from litestar.typing import FieldDefinition
from litestar.utils import AsyncCallable, Ref, async_partial, get_name, normalize_path
from litestar.utils.helpers import unwrap_partial
from litestar.utils.predicates import is_async_callable
from litestar.utils.signature import ParsedSignature, infer_request_encoding_from_field_definition

if TYPE_CHECKING:
    from typing_extensions import Self

    from litestar import Litestar
    from litestar.connection import ASGIConnection
    from litestar.controller import Controller
    from litestar.dto.interface import DTOInterface
    from litestar.params import ParameterKwarg
    from litestar.plugins import SerializationPluginProtocol
    from litestar.router import Router
    from litestar.types import AnyCallable, AsyncAnyCallable, ExceptionHandler
    from litestar.types.empty import EmptyType

__all__ = ("BaseRouteHandler",)


class BaseRouteHandler:
    """Base route handler.

    Serves as a subclass for all route handlers
    """

    __slots__ = (
        "_fn",
        "_parsed_fn_signature",
        "_resolved_dependencies",
        "_resolved_dto",
        "_resolved_guards",
        "_resolved_layered_parameters",
        "_resolved_return_dto",
        "_resolved_signature_namespace",
        "_resolved_type_decoders",
        "_resolved_type_encoders",
        "dependencies",
        "dto",
        "exception_handlers",
        "guards",
        "middleware",
        "name",
        "opt",
        "owner",
        "paths",
        "return_dto",
        "signature_model",
        "signature_namespace",
        "type_decoders",
        "type_encoders",
    )

    def __init__(
        self,
        path: str | Sequence[str] | None = None,
        *,
        dependencies: Dependencies | None = None,
        dto: type[DTOInterface] | None | EmptyType = Empty,
        exception_handlers: ExceptionHandlersMap | None = None,
        guards: Sequence[Guard] | None = None,
        middleware: Sequence[Middleware] | None = None,
        name: str | None = None,
        opt: Mapping[str, Any] | None = None,
        return_dto: type[DTOInterface] | None | EmptyType = Empty,
        signature_namespace: Mapping[str, Any] | None = None,
        type_encoders: TypeEncodersMap | None = None,
        type_decoders: TypeDecodersSequence | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ``HTTPRouteHandler``.

        Args:
            path: A path fragment for the route handler function or a sequence of path fragments. If not given defaults
                to ``/``
            dependencies: A string keyed mapping of dependency :class:`Provider <.di.Provide>` instances.
            dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for (de)serializing and
                validation of request data.
            exception_handlers: A mapping of status codes and/or exception types to handler functions.
            guards: A sequence of :class:`Guard <.types.Guard>` callables.
            middleware: A sequence of :class:`Middleware <.types.Middleware>`.
            name: A string identifying the route handler.
            opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
                wherever you have access to :class:`Request <.connection.Request>` or
                :class:`ASGI Scope <.types.Scope>`.
            return_dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for serializing
                outbound response data.
            signature_namespace: A mapping of names to types for use in forward reference resolution during signature
                modelling.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            type_decoders: A sequence of tuples, each composed of a predicate testing for type identity and a msgspec hook for deserialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        self._parsed_fn_signature: ParsedSignature | EmptyType = Empty
        self._resolved_dependencies: dict[str, Provide] | EmptyType = Empty
        self._resolved_dto: type[DTOInterface] | None | EmptyType = Empty
        self._resolved_guards: list[Guard] | EmptyType = Empty
        self._resolved_layered_parameters: dict[str, FieldDefinition] | EmptyType = Empty
        self._resolved_return_dto: type[DTOInterface] | None | EmptyType = Empty
        self._resolved_signature_namespace: dict[str, Any] | EmptyType = Empty
        self._resolved_type_encoders: TypeEncodersMap | EmptyType = Empty
        self._resolved_type_decoders: TypeDecodersSequence | EmptyType = Empty

        self.dependencies = dependencies
        self.dto = dto
        self.exception_handlers = exception_handlers
        self.guards = guards
        self.middleware = middleware
        self.name = name
        self.opt = dict(opt or {})
        self.owner: Controller | Router | None = None
        self.return_dto = return_dto
        self.signature_model: type[SignatureModel] | None = None
        self.signature_namespace = signature_namespace or {}
        self.paths = (
            {normalize_path(p) for p in path}
            if path and isinstance(path, list)
            else {normalize_path(path or "/")}  # type: ignore
        )
        self.opt.update(**kwargs)
        self.type_encoders = type_encoders
        self.type_decoders = type_decoders

    def __call__(self, fn: AsyncAnyCallable) -> Self:
        """Replace a function with itself."""
        self._fn = Ref["MaybePartial[AsyncAnyCallable]"](fn)
        return self

    @property
    def default_deserializer(self) -> Callable[[Any, Any], Any]:
        """Get a default serializer for the route handler.

        Returns:
            A default serializer for the route handler.

        """
        return partial(default_deserializer, type_decoders=self.resolve_type_decoders())

    @property
    def fn(self) -> Ref[MaybePartial[AsyncAnyCallable]]:
        """Get the handler function.

        Raises:
            ImproperlyConfiguredException: if handler fn is not set.

        Returns:
            Handler function
        """
        if not hasattr(self, "_fn"):
            raise ImproperlyConfiguredException("Handler has not decorated a function")
        return self._fn

    @property
    def parsed_fn_signature(self) -> ParsedSignature:
        """Return the parsed signature of the handler function.

        This method is memoized so the computation occurs only once.

        Returns:
            A ParsedSignature instance
        """
        if self._parsed_fn_signature is Empty:
            self._parsed_fn_signature = ParsedSignature.from_fn(
                unwrap_partial(self.fn.value), self.resolve_signature_namespace()
            )

        return cast("ParsedSignature", self._parsed_fn_signature)

    @property
    def handler_name(self) -> str:
        """Get the name of the handler function.

        Raises:
            ImproperlyConfiguredException: if handler fn is not set.

        Returns:
            Name of the handler function
        """
        return get_name(unwrap_partial(self.fn.value))

    @property
    def dependency_name_set(self) -> set[str]:
        """Set of all dependency names provided in the handler's ownership layers."""
        layered_dependencies = (layer.dependencies or {} for layer in self.ownership_layers)
        return {name for layer in layered_dependencies for name in layer}  # pyright: ignore

    @property
    def ownership_layers(self) -> list[Self | Controller | Router]:
        """Return the handler layers from the app down to the route handler.

        ``app -> ... -> route handler``
        """
        layers = []

        cur: Any = self
        while cur:
            layers.append(cur)
            cur = cur.owner

        return list(reversed(layers))

    def resolve_type_encoders(self) -> TypeEncodersMap:
        """Return a merged type_encoders mapping.

        This method is memoized so the computation occurs only once.

        Returns:
            A dict of type encoders
        """
        if self._resolved_type_encoders is Empty:
            self._resolved_type_encoders = {}

            for layer in self.ownership_layers:
                if type_encoders := getattr(layer, "type_encoders", None):
                    self._resolved_type_encoders.update(type_encoders)
        return cast("TypeEncodersMap", self._resolved_type_encoders)

    def resolve_type_decoders(self) -> TypeDecodersSequence:
        """Return a merged type_encoders mapping.

        This method is memoized so the computation occurs only once.

        Returns:
            A dict of type encoders
        """
        if self._resolved_type_decoders is Empty:
            self._resolved_type_decoders = []

            for layer in self.ownership_layers:
                if type_decoders := getattr(layer, "type_decoders", None):
                    self._resolved_type_decoders.extend(list(type_decoders))
        return cast("TypeDecodersSequence", self._resolved_type_decoders)

    def resolve_layered_parameters(self) -> dict[str, FieldDefinition]:
        """Return all parameters declared above the handler."""
        if self._resolved_layered_parameters is Empty:
            parameter_kwargs: dict[str, ParameterKwarg] = {}

            for layer in self.ownership_layers:
                parameter_kwargs.update(getattr(layer, "parameters", {}) or {})

            self._resolved_layered_parameters = {
                key: FieldDefinition.from_kwarg(name=key, annotation=parameter.annotation, kwarg_definition=parameter)
                for key, parameter in parameter_kwargs.items()
            }

        return cast("dict[str, FieldDefinition]", self._resolved_layered_parameters)

    def resolve_guards(self) -> list[Guard]:
        """Return all guards in the handlers scope, starting from highest to current layer."""
        if self._resolved_guards is Empty:
            self._resolved_guards = []

            for layer in self.ownership_layers:
                self._resolved_guards.extend(layer.guards or [])  # pyright: ignore

            self._resolved_guards = cast("list[Guard]", [AsyncCallable(guard) for guard in self._resolved_guards])

        return self._resolved_guards  # type:ignore

    def resolve_dependencies(self) -> dict[str, Provide]:
        """Return all dependencies correlating to handler function's kwargs that exist in the handler's scope."""
        if self._resolved_dependencies is Empty:
            self._resolved_dependencies = {}

            for layer in self.ownership_layers:
                for key, value in (layer.dependencies or {}).items():
                    if not isinstance(value, Provide):
                        value = Provide(value)
                    self._validate_dependency_is_unique(
                        dependencies=self._resolved_dependencies, key=key, provider=value
                    )
                    self._resolved_dependencies[key] = value

        return cast("dict[str, Provide]", self._resolved_dependencies)

    def resolve_middleware(self) -> list[Middleware]:
        """Build the middleware stack for the RouteHandler and return it.

        The middlewares are added from top to bottom (``app -> router -> controller -> route handler``) and then
        reversed.
        """
        resolved_middleware: list[Middleware] = []
        for layer in self.ownership_layers:
            resolved_middleware.extend(layer.middleware or [])  # pyright: ignore
        return list(reversed(resolved_middleware))

    def resolve_exception_handlers(self) -> ExceptionHandlersMap:
        """Resolve the exception_handlers by starting from the route handler and moving up.

        This method is memoized so the computation occurs only once.
        """
        resolved_exception_handlers: dict[int | type[Exception], ExceptionHandler] = {}
        for layer in self.ownership_layers:
            resolved_exception_handlers.update(layer.exception_handlers or {})  # pyright: ignore
        return resolved_exception_handlers

    def resolve_opts(self) -> None:
        """Build the route handler opt dictionary by going from top to bottom.

        When merging keys from multiple layers, if the same key is defined by multiple layers, the value from the
        layer closest to the response handler will take precedence.
        """

        opt: dict[str, Any] = {}
        for layer in self.ownership_layers:
            opt.update(layer.opt or {})  # pyright: ignore

        self.opt = opt

    def resolve_signature_namespace(self) -> dict[str, Any]:
        """Build the route handler signature namespace dictionary by going from top to bottom.

        When merging keys from multiple layers, if the same key is defined by multiple layers, the value from the
        layer closest to the response handler will take precedence.
        """
        if self._resolved_layered_parameters is Empty:
            ns: dict[str, Any] = {}
            for layer in self.ownership_layers:
                ns.update(layer.signature_namespace)

            self._resolved_signature_namespace = ns
        return cast("dict[str, Any]", self._resolved_signature_namespace)

    def resolve_dto(self) -> type[DTOInterface] | None:
        """Resolve the data_dto by starting from the route handler and moving up.
        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once.

        Returns:
            An optional :class:`DTO type <.dto.interface.DTOInterface>`
        """
        if self._resolved_dto is Empty:
            dtos: list[type[DTOInterface] | None] = [
                layer_dto  # type:ignore[misc]
                for layer in self.ownership_layers
                if (layer_dto := layer.dto) is not Empty
            ]
            self._resolved_dto = dtos[-1] if dtos else None

        return cast("type[DTOInterface] | None", self._resolved_dto)

    def resolve_return_dto(self) -> type[DTOInterface] | None:
        """Resolve the return_dto by starting from the route handler and moving up.
        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once.

        Returns:
            An optional :class:`DTO type <.dto.interface.DTOInterface>`
        """
        if self._resolved_return_dto is Empty:
            return_dtos: list[type[DTOInterface] | None] = [
                layer_dto_type  # type:ignore[misc]
                for layer in self.ownership_layers
                if (layer_dto_type := layer.return_dto) is not Empty
            ]
            self._resolved_return_dto = return_dtos[-1] if return_dtos else self.resolve_dto()

        return cast("type[DTOInterface] | None", self._resolved_return_dto)

    def _set_dto(self, dto: type[DTOInterface]) -> None:
        """Set the dto for the handler.

        Args:
            dto: The :class:`DTO type <.dto.interface.DTOInterface>` to set.
        """
        self._resolved_dto = dto

    def _set_return_dto(self, dto: type[DTOInterface]) -> None:
        """Set the return_dto for the handler.

        Args:
            dto: The :class:`DTO type <.dto.interface.DTOInterface>` to set.
        """
        self._resolved_return_dto = dto

    def _init_handler_dtos(self) -> None:
        """Initialize the data and return DTOs for the handler."""
        if (dto := self.resolve_dto()) and (data_parameter := self.parsed_fn_signature.parameters.get("data")):
            dto.on_registration(
                HandlerContext(
                    dto_for="data",
                    handler_id=str(self),
                    field_definition=data_parameter,
                    request_encoding_type=infer_request_encoding_from_field_definition(data_parameter),
                )
            )

        if return_dto := self.resolve_return_dto():
            return_dto.on_registration(
                HandlerContext(
                    dto_for="return", handler_id=str(self), field_definition=self.parsed_fn_signature.return_type
                )
            )

    async def authorize_connection(self, connection: ASGIConnection) -> None:
        """Ensure the connection is authorized by running all the route guards in scope."""
        for guard in self.resolve_guards():
            await guard(connection, copy(self))  # type: ignore

    @staticmethod
    def _validate_dependency_is_unique(dependencies: dict[str, Provide], key: str, provider: Provide) -> None:
        """Validate that a given provider has not been already defined under a different key."""
        for dependency_key, value in dependencies.items():
            if provider == value:
                raise ImproperlyConfiguredException(
                    f"Provider for key {key} is already defined under the different key {dependency_key}. "
                    f"If you wish to override a provider, it must have the same key."
                )

    def on_registration(self, app: Litestar) -> None:
        """Called once per handler when the app object is instantiated."""
        self._validate_handler_function()
        self._handle_serialization_plugins(app.serialization_plugins)
        self._init_handler_dtos()
        self._set_runtime_callables()
        self._create_signature_model(app)
        self._create_provider_signature_models(app)
        self.resolve_guards()
        self.resolve_middleware()
        self.resolve_opts()

    def _validate_handler_function(self) -> None:
        """Validate the route handler function once set by inspecting its return annotations."""

    def _set_runtime_callables(self) -> None:
        """Optimize the ``route_handler.fn`` and any ``provider.dependency`` callables for runtime by doing the following:

        1. ensure that the ``self`` argument is preserved by binding it using partial.
        2. ensure sync functions are wrapped in AsyncCallable for sync_to_thread handlers.
        """
        for provider in self.resolve_dependencies().values():
            if not is_async_callable(provider.dependency.value):
                provider.has_sync_callable = False
                if provider.sync_to_thread:
                    provider.dependency.value = async_partial(provider.dependency.value)
                else:
                    provider.has_sync_callable = True

    def _create_signature_model(self, app: Litestar) -> None:
        """Create signature model for handler function."""
        if not self.signature_model:
            self.signature_model = SignatureModel.create(
                dependency_name_set=self.dependency_name_set,
                fn=cast("AnyCallable", self.fn.value),
                parsed_signature=self.parsed_fn_signature,
                has_data_dto=bool(self.resolve_dto()),
            )

    def _create_provider_signature_models(self, app: Litestar) -> None:
        """Create signature models for dependency providers."""
        for provider in self.resolve_dependencies().values():
            if not getattr(provider, "signature_model", None):
                provider.signature_model = SignatureModel.create(
                    dependency_name_set=self.dependency_name_set,
                    fn=provider.dependency.value,
                    parsed_signature=ParsedSignature.from_fn(
                        unwrap_partial(provider.dependency.value), self.resolve_signature_namespace()
                    ),
                    has_data_dto=bool(self.resolve_dto()),
                )

    def _handle_serialization_plugins(self, plugins: list[SerializationPluginProtocol]) -> None:
        """Handle the serialization plugins for the handler."""
        # must do the return dto first, otherwise it will resolve to the same as the data dto
        if self.resolve_return_dto() is None:
            return_type = self.parsed_fn_signature.return_type
            for plugin in plugins:
                if plugin.supports_type(return_type):
                    self._set_return_dto(plugin.create_dto_for_type(return_type))
                    break

        if (data_param := self.parsed_fn_signature.parameters.get("data")) and self.resolve_dto() is None:
            for plugin in plugins:
                if plugin.supports_type(data_param):
                    self._set_dto(plugin.create_dto_for_type(data_param))
                    break

    def __str__(self) -> str:
        """Return a unique identifier for the route handler.

        Returns:
            A string
        """
        target: type[AsyncAnyCallable] | AsyncAnyCallable
        target = unwrap_partial(self.fn.value)
        if not hasattr(target, "__qualname__"):
            target = type(target)
        return f"{target.__module__}.{target.__qualname__}"
