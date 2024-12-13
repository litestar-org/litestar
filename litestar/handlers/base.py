from __future__ import annotations

from functools import partial
from typing import TYPE_CHECKING, Any, Callable, Iterable, Mapping, Sequence, cast

from litestar._signature import SignatureModel
from litestar.di import Provide
from litestar.dto import DTOData
from litestar.exceptions import ImproperlyConfiguredException, LitestarException
from litestar.plugins import DIPlugin
from litestar.serialization import default_deserializer, default_serializer
from litestar.types import (
    Dependencies,
    Empty,
    ExceptionHandlersMap,
    Guard,
    Middleware,
    TypeDecodersSequence,
    TypeEncodersMap,
    ParametersMap,
)
from litestar.typing import FieldDefinition
from litestar.utils import ensure_async_callable, get_name, join_paths, normalize_path
from litestar.utils.deprecation import deprecated
from litestar.utils.empty import value_or_default
from litestar.utils.helpers import unwrap_partial
from litestar.utils.signature import ParsedSignature, add_types_to_signature_namespace, merge_signature_namespaces

if TYPE_CHECKING:
    from typing_extensions import Self

    from litestar._kwargs import KwargsModel
    from litestar.app import Litestar
    from litestar.connection import ASGIConnection
    from litestar.controller import Controller
    from litestar.dto import AbstractDTO
    from litestar.router import Router
    from litestar.routes import BaseRoute
    from litestar.types import AsyncAnyCallable, ExceptionHandler
    from litestar.types.empty import EmptyType

__all__ = ("BaseRouteHandler",)


class BaseRouteHandler:
    """Base route handler.

    Serves as a subclass for all route handlers
    """

    __slots__ = (
        "_parsed_data_field",
        "_parsed_fn_signature",
        "_parsed_return_field",
        "_resolved_data_dto",
        "_parameter_field_definitions",
        "_resolved_return_dto",
        "_resolved_signature_namespace",
        "_resolved_signature_model",
        "_registered",
        "dependencies",
        "dto",
        "exception_handlers",
        "fn",
        "guards",
        "middleware",
        "name",
        "opt",
        "paths",
        "return_dto",
        "signature_namespace",
        "type_decoders",
        "type_encoders",
        "parameters",
    )

    def __init__(
        self,
        path: str | Sequence[str] | None = None,
        *,
        fn: AsyncAnyCallable,
        dependencies: Dependencies | None = None,
        dto: type[AbstractDTO] | None | EmptyType = Empty,
        exception_handlers: ExceptionHandlersMap | None = None,
        guards: Sequence[Guard] | None = None,
        middleware: Sequence[Middleware] | None = None,
        name: str | None = None,
        opt: Mapping[str, Any] | None = None,
        return_dto: type[AbstractDTO] | None | EmptyType = Empty,
        signature_namespace: Mapping[str, Any] | None = None,
        signature_types: Sequence[Any] | None = None,
        parameters: ParametersMap | None = None,
        type_decoders: TypeDecodersSequence | None = None,
        type_encoders: TypeEncodersMap | None = None,
        **kwargs: Any,
    ) -> None:
        """Initialize ``HTTPRouteHandler``.

        Args:
            path: A path fragment for the route handler function or a sequence of path fragments. If not given defaults
                to ``/``
            fn: The handler function

                .. versionadded:: 3.0
            dependencies: A string keyed mapping of dependency :class:`Provider <.di.Provide>` instances.
            dto: :class:`AbstractDTO <.dto.base_dto.AbstractDTO>` to use for (de)serializing and
                validation of request data.
            exception_handlers: A mapping of status codes and/or exception types to handler functions.
            guards: A sequence of :class:`Guard <.types.Guard>` callables.
            middleware: A sequence of :class:`Middleware <.types.Middleware>`.
            name: A string identifying the route handler.
            opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
                wherever you have access to :class:`Request <.connection.Request>` or
                :class:`ASGI Scope <.types.Scope>`.
            return_dto: :class:`AbstractDTO <.dto.base_dto.AbstractDTO>` to use for serializing
                outbound response data.
            signature_namespace: A mapping of names to types for use in forward reference resolution during signature
                modelling.
            signature_types: A sequence of types for use in forward reference resolution during signature modeling.
                These types will be added to the signature namespace using their ``__name__`` attribute.
            type_decoders: A sequence of tuples, each composed of a predicate testing for type identity and a msgspec hook for deserialization.
            type_encoders: A mapping of types to callables that transform them into types supported for serialization.
            **kwargs: Any additional kwarg - will be set in the opt dictionary.
        """
        self._parsed_fn_signature: ParsedSignature | EmptyType = Empty
        self._parsed_return_field: FieldDefinition | EmptyType = Empty
        self._parsed_data_field: FieldDefinition | None | EmptyType = Empty
        self._resolved_data_dto: type[AbstractDTO] | None | EmptyType = Empty
        self._parameter_field_definitions: dict[str, FieldDefinition] | EmptyType = Empty
        self._resolved_return_dto: type[AbstractDTO] | None | EmptyType = Empty
        self._resolved_signature_namespace: dict[str, Any] | EmptyType = Empty
        self._resolved_signature_model: type[SignatureModel] | EmptyType = Empty
        self._registered = False

        self.dependencies = (
            {
                key: provider if isinstance(provider, Provide) else Provide(provider)
                for key, provider in dependencies.items()
            }
            if dependencies
            else {}
        )
        self.dto = dto
        self.exception_handlers = exception_handlers or {}
        self.guards = tuple(ensure_async_callable(guard) for guard in guards) if guards else ()
        self.middleware = tuple(middleware) if middleware else ()
        self.name = name
        self.opt = dict(opt or {})
        self.opt.update(**kwargs)
        self.return_dto = return_dto
        self.signature_namespace = add_types_to_signature_namespace(
            signature_types or [], dict(signature_namespace or {})
        )
        self.type_decoders = type_decoders or ()
        self.type_encoders = type_encoders or {}
        self.paths = (
            {normalize_path(p) for p in path} if path and isinstance(path, list) else {normalize_path(path or "/")}  # type: ignore[arg-type]
        )
        self.fn = fn
        self.parameters = parameters or {}

    def merge(self, other: Controller | Router) -> Self:
        return BaseRouteHandler(
            path=[join_paths([other.path, p]) for p in self.paths],
            fn=self.fn,
            dependencies={**(other.dependencies or {}), **self.dependencies},
            dto=value_or_default(self.dto, other.dto),
            return_dto=value_or_default(self.return_dto, other.return_dto),
            exception_handlers={**(other.exception_handlers or {}), **self.exception_handlers},
            guards=[*(other.guards or []), *self.guards],
            middleware=[*(other.middleware or ()), *self.middleware],
            name=self.name,
            opt={**other.opt, **self.opt},
            signature_namespace={**other.signature_namespace, **self.signature_namespace},
            signature_types=other.signature_types,
            type_decoders=(*(other.type_decoders or ()), *self.type_decoders),
            type_encoders={**(other.type_encoders or {}), **self.type_encoders},
            parameters={**other.parameters, **self.parameters},
        )

    def finalize(self) -> Self:
        return self

    @property
    def handler_id(self) -> str:
        """A unique identifier used for generation of DTOs."""
        return f"{self!s}::{sum(id(layer) for layer in self._ownership_layers)}"

    @property
    def default_deserializer(self) -> Callable[[Any, Any], Any]:
        """Get a default deserializer for the route handler.

        Returns:
            A default deserializer for the route handler.

        """
        return partial(default_deserializer, type_decoders=self.type_decoders)

    @property
    def default_serializer(self) -> Callable[[Any], Any]:
        """Get a default serializer for the route handler.

        Returns:
            A default serializer for the route handler.

        """
        return partial(default_serializer, type_encoders=self.type_encoders)

    @property
    def _signature_model(self) -> type[SignatureModel]:
        """Get the signature model for the route handler.

        Returns:
            A signature model for the route handler.

        """
        if self._resolved_signature_model is Empty:
            self._resolved_signature_model = SignatureModel.create(
                dependency_name_set=set(self.dependencies.keys()),
                fn=cast("AnyCallable", self.fn),
                parsed_signature=self.parsed_fn_signature,
                data_dto=self.resolve_data_dto(),
                type_decoders=self.type_decoders,
            )
        return self._resolved_signature_model

    @property
    def parsed_fn_signature(self) -> ParsedSignature:
        """Return the parsed signature of the handler function.

        This method is memoized so the computation occurs only once.

        Returns:
            A ParsedSignature instance
        """
        if self._parsed_fn_signature is Empty:
            self._parsed_fn_signature = ParsedSignature.from_fn(
                unwrap_partial(self.fn), self._resolve_signature_namespace()
            )

        return self._parsed_fn_signature

    @property
    def parsed_return_field(self) -> FieldDefinition:
        if self._parsed_return_field is Empty:
            self._parsed_return_field = self.parsed_fn_signature.return_type
        return self._parsed_return_field

    @property
    def parsed_data_field(self) -> FieldDefinition | None:
        if self._parsed_data_field is Empty:
            self._parsed_data_field = self.parsed_fn_signature.parameters.get("data")
        return self._parsed_data_field

    @property
    def handler_name(self) -> str:
        """Get the name of the handler function.

        Raises:
            ImproperlyConfiguredException: if handler fn is not set.

        Returns:
            Name of the handler function
        """
        return get_name(unwrap_partial(self.fn))

    @property
    def _ownership_layers(self) -> list[Self | Controller | Router]:
        """Return the handler layers from the app down to the route handler.

        ``app -> ... -> route handler``
        """
        return [self]

    def _check_registered(self) -> None:
        if not self._registered:
            raise LitestarException(
                f"Handler {self!r}: Accessing this attribute is unsafe until the handler has been"
                "registered with an application, as it may yield different results after registration."
            )

    @deprecated("3.0", removal_in="4.0", alternative=".type_encoders attribute")
    def resolve_type_encoders(self) -> TypeEncodersMap:
        """Return a merged type_encoders mapping.

        Returns:
            A dict of type encoders
        """
        self._check_registered()
        return self.type_encoders

    @deprecated("3.0", removal_in="4.0", alternative=".type_decoders attribute")
    def resolve_type_decoders(self) -> TypeDecodersSequence:
        """Return a merged type_encoders mapping.

        Returns:
            A dict of type encoders
        """
        self._check_registered()
        return self.type_decoders

    @deprecated("3.0", removal_in="4.0", alternative=".parameter_field_definitions property")
    def resolve_layered_parameters(self) -> dict[str, FieldDefinition]:
        self._check_registered()
        return self.parameter_field_definitions

    @property
    def parameter_field_definitions(self) -> dict[str, FieldDefinition]:
        """Return all parameters declared above the handler."""
        if self._parameter_field_definitions is Empty:
            self._check_registered()
            self._parameter_field_definitions = {
                key: FieldDefinition.from_kwarg(name=key, annotation=parameter.annotation, kwarg_definition=parameter)
                for key, parameter in self.parameters.items()
            }
        return self._parameter_field_definitions

    @deprecated("3.0", removal_in="4.0", alternative=".guards attribute")
    def resolve_guards(self) -> tuple[Guard, ...]:
        """Return all guards in the handlers scope, starting from highest to current layer."""
        self._check_registered()
        return self.guards

    @deprecated("3.0", removal_in="4.0", alternative=".dependencies attribute")
    def resolve_dependencies(self) -> dict[str, Provide]:
        """Return all dependencies correlating to handler function's kwargs that exist in the handler's scope."""
        self._check_registered()
        return self.dependencies

    def _finalize_dependencies(self, app: Litestar | None = None):
        dependencies: dict[str, Provide] = {}

        # keep track of which providers are available for each dependency
        provider_keys: dict[Any, str] = {}

        for key, provider in self.dependencies.items():
            # ensure that if a provider for this dependency has already been registered,
            # registering this provider again is only allowed as an override, i.e. with
            # the same key
            if (existing_key := provider_keys.get(provider.dependency)) and existing_key != key:
                raise ImproperlyConfiguredException(
                    f"Provider for {provider.dependency!r} with key {key!r} is already defined under a different key "
                    f"{existing_key!r}. If you wish to override a provider, it must have the same key."
                )

            provider_keys[provider.dependency] = key

            # TODO: Move this part to 'Provide'
            if not getattr(provider, "parsed_fn_signature", None):
                dependency = unwrap_partial(provider.dependency)
                plugin: DIPlugin | None = None
                if app:
                    plugin = next(
                        (p for p in app.plugins.di if isinstance(p, DIPlugin) and p.has_typed_init(dependency)),
                        None,
                    )
                if plugin:
                    signature, init_type_hints = plugin.get_typed_init(dependency)
                    provider.parsed_fn_signature = ParsedSignature.from_signature(signature, init_type_hints)
                else:
                    provider.parsed_fn_signature = ParsedSignature.from_fn(
                        dependency, self._resolve_signature_namespace()
                    )

            if not getattr(provider, "signature_model", None):
                provider.signature_model = SignatureModel.create(
                    dependency_name_set=set(self.dependencies.keys()),
                    fn=provider.dependency,
                    parsed_signature=provider.parsed_fn_signature,
                    data_dto=self.resolve_data_dto(app=app),
                    type_decoders=self.type_decoders,
                )
            dependencies[key] = provider

    @deprecated("3.0", removal_in="4.0", alternative=".middleware attribute")
    def resolve_middleware(self) -> tuple[Middleware, ...]:
        """Return registered middlewares"""
        self._check_registered()
        return self.middleware

    @deprecated("3.0", removal_in="4.0", alternative=".exception_handlers attribute")
    def resolve_exception_handlers(self) -> ExceptionHandlersMap:
        """Resolve the exception_handlers by starting from the route handler and moving up.

        This method is memoized so the computation occurs only once.
        """
        self._check_registered()
        return self.exception_handlers

    def _resolve_opts(self) -> None:
        """Build the route handler opt dictionary by going from top to bottom.

        When merging keys from multiple layers, if the same key is defined by multiple layers, the value from the
        layer closest to the response handler will take precedence.
        """

        opt: dict[str, Any] = {}
        for layer in self._ownership_layers:
            opt.update(layer.opt or {})  # pyright: ignore

        self.opt = opt

    def _resolve_signature_namespace(self) -> dict[str, Any]:
        """Build the route handler signature namespace dictionary by going from top to bottom.

        When merging keys from multiple layers, if the same key is defined by multiple layers, the value from the
        layer closest to the response handler will take precedence.
        """
        if self._resolved_signature_namespace is Empty:
            ns: dict[str, Any] = {}
            for layer in self._ownership_layers:
                merge_signature_namespaces(
                    signature_namespace=ns, additional_signature_namespace=layer.signature_namespace
                )
            self._resolved_signature_namespace = ns
        return self._resolved_signature_namespace

    def resolve_data_dto(self, app: Litestar | None = None) -> type[AbstractDTO] | None:
        """Resolve the data_dto by starting from the route handler and moving up.
        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once.

        Returns:
            An optional :class:`DTO type <.dto.base_dto.AbstractDTO>`
        """
        if self._resolved_data_dto is Empty:
            if data_dtos := cast(
                "list[type[AbstractDTO] | None]",
                [layer.dto for layer in self._ownership_layers if layer.dto is not Empty],
            ):
                data_dto: type[AbstractDTO] | None = data_dtos[-1]
            elif self.parsed_data_field and (
                plugins_for_data_type := [
                    plugin
                    for plugin in app.plugins.serialization
                    if self.parsed_data_field.match_predicate_recursively(plugin.supports_type)
                ]
            ):
                data_dto = plugins_for_data_type[0].create_dto_for_type(self.parsed_data_field)
            else:
                data_dto = None

            if self.parsed_data_field and data_dto:
                data_dto.create_for_field_definition(
                    field_definition=self.parsed_data_field,
                    handler_id=self.handler_id,
                )

            self._resolved_data_dto = data_dto

        return self._resolved_data_dto

    def resolve_return_dto(self, app: Litestar | None = None) -> type[AbstractDTO] | None:
        """Resolve the return_dto by starting from the route handler and moving up.
        If a handler is found it is returned, otherwise None is set.
        This method is memoized so the computation occurs only once.

        Returns:
            An optional :class:`DTO type <.dto.base_dto.AbstractDTO>`
        """
        if self._resolved_return_dto is Empty:
            if return_dtos := cast(
                "list[type[AbstractDTO] | None]",
                [layer.return_dto for layer in self._ownership_layers if layer.return_dto is not Empty],
            ):
                return_dto: type[AbstractDTO] | None = return_dtos[-1]
            elif plugins_for_return_type := [
                plugin
                for plugin in app.plugins.serialization
                if self.parsed_return_field.match_predicate_recursively(plugin.supports_type)
            ]:
                return_dto = plugins_for_return_type[0].create_dto_for_type(self.parsed_return_field)
            else:
                return_dto = self.resolve_data_dto(app=app)

            if return_dto and return_dto.is_supported_model_type_field(self.parsed_return_field):
                return_dto.create_for_field_definition(
                    field_definition=self.parsed_return_field,
                    handler_id=self.handler_id,
                )
                self._resolved_return_dto = return_dto
            else:
                self._resolved_return_dto = None

        return self._resolved_return_dto

    async def authorize_connection(self, connection: ASGIConnection) -> None:
        """Ensure the connection is authorized by running all the route guards in scope."""
        for guard in self.guards:
            await guard(connection, self)  # type: ignore[misc]

    def on_registration(self, route: BaseRoute, app: Litestar) -> None:
        """Called once per handler when the app object is instantiated.

        Args:
            route: The route this handler is being registered on

        Returns:
            None
        """
        self._registered = True

        # due to the way we're traversing over the app layers, the middleware stack is
        # constructed in the wrong order (handler > application). reversing the order
        # here is easier than handling it correctly at every intermediary step
        self.middleware = tuple(reversed(self.middleware))

        self._validate_handler_function(app=app)
        self._finalize_dependencies(app=app)
        self.resolve_data_dto(app=app)
        self.resolve_return_dto(app=app)
        self._resolve_opts()

    def _validate_handler_function(self, app: Litestar | None = None) -> None:
        """Validate the route handler function once set by inspecting its return annotations."""
        if (
            self.parsed_data_field is not None
            and self.parsed_data_field.is_subclass_of(DTOData)
            and not self.resolve_data_dto(app=app)
        ):
            raise ImproperlyConfiguredException(
                f"Handler function {self.handler_name} has a data parameter that is a subclass of DTOData but no "
                "DTO has been registered for it."
            )

    def __str__(self) -> str:
        """Return a unique identifier for the route handler.

        Returns:
            A string
        """
        target: type[AsyncAnyCallable] | AsyncAnyCallable  # pyright: ignore
        target = unwrap_partial(self.fn)
        if not hasattr(target, "__qualname__"):
            target = type(target)
        return f"{target.__module__}.{target.__qualname__}"

    def _create_kwargs_model(
        self,
        path_parameters: Iterable[str],
    ) -> KwargsModel:
        """Create a `KwargsModel` for a given route handler."""
        from litestar._kwargs import KwargsModel

        return KwargsModel.create_for_signature_model(
            signature_model=self._signature_model,
            parsed_signature=self.parsed_fn_signature,
            dependencies=self.dependencies,
            path_parameters=set(path_parameters),
            layered_parameters=self.parameter_field_definitions,
        )
