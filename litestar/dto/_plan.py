from __future__ import annotations

import dataclasses
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

import msgspec

from litestar._layers.errors import HandlerErrorPrefix
from litestar.dto._backend import DTOBackend, _qualified_name
from litestar.dto._registry import TransferModelNaming, TransferModelRegistry, handler_name_scope
from litestar.dto.data_structures import DTOData
from litestar.exceptions.dto_exceptions import (
    DTOFactoryException,
    DTOTransferTypeError,
    InvalidAnnotationException,
    MissingDTOError,
)
from litestar.params import BodyKwarg
from litestar.response.base import Response
from litestar.types import Empty
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable

    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.app import Litestar
    from litestar.connection import ASGIConnection
    from litestar.dto.base_dto import AbstractDTO
    from litestar.handlers.base import BaseRouteHandler
    from litestar.openapi.spec import Reference, Schema
    from litestar.plugins import SerializationPlugin
    from litestar.types.empty import EmptyType
    from litestar.types.serialization import LitestarEncodableType

__all__ = (
    "DTODeclaration",
    "DTODirectionPlan",
    "DTOPlan",
    "DecodeFn",
    "EncodeFn",
    "build_dto_plan",
    "build_schema_annotation",
    "create_backend",
    "create_dto_openapi_schema",
    "dto_name",
    "read_dto_declaration",
    "take_plan_build",
)

DecodeFn: TypeAlias = "Callable[[Any, ASGIConnection[Any, Any, Any, Any]], Any]"
EncodeFn: TypeAlias = "Callable[[Any, ASGIConnection[Any, Any, Any, Any]], LitestarEncodableType]"


@dataclass(frozen=True, slots=True)
class DTODirectionPlan:
    """How a route handler applies a DTO in one direction, to the data it receives or to the data it returns."""

    dto: type[AbstractDTO[Any]]
    """The DTO class applied in this direction"""
    backend: DTOBackend
    """The backend built for the handler's own field in this direction, bound to the handler's type decoders"""
    schema_annotation: Any
    """The annotation the field is documented with in the OpenAPI schema"""


@dataclass(frozen=True, slots=True)
class DTOPlan:
    """How a route handler applies its DTOs. Built once by :func:`build_dto_plan` when the handler is registered,
    stored on the handler and never modified.
    """

    data: DTODirectionPlan | None
    """The DTO applied to the data the handler receives. ``None`` if no DTO applies to it, or if the handler
    receives no data
    """
    return_: DTODirectionPlan | None
    """The DTO applied to the data the handler returns. ``None`` if no DTO applies to it"""
    data_dto: type[AbstractDTO[Any]] | None
    """The resolved data DTO class. It may be set while :attr:`data` is ``None``, for a handler configured with a
    ``dto`` that receives no data
    """
    decode_bytes: DecodeFn | None
    """Decode raw request data with the data DTO. Set exactly when :attr:`data` is set"""
    decode_builtins: DecodeFn | None
    """Decode builtin values, such as form data, with the data DTO. Set exactly when :attr:`data` is set"""
    encode: EncodeFn | None
    """Encode returned data with the return DTO. Set exactly when :attr:`return_` is set"""


@dataclass(frozen=True, slots=True)
class DTODeclaration:
    """A route handler's declaration of one of its DTO options, and where it comes from."""

    option: Literal["dto", "return_dto"]
    """The option declared"""
    value: type[AbstractDTO[Any]] | None | EmptyType
    """The declared value, ``Empty`` if neither the handler nor a layer above it declares the option"""
    source: Literal["handler", "layer"] | None
    """``"handler"`` if the handler declares the option itself, ``"layer"`` if a layer above it does, ``None`` if
    :attr:`value` is ``Empty``
    """


def read_dto_declaration(handler: BaseRouteHandler, option: Literal["dto", "return_dto"]) -> DTODeclaration:
    """Return the declaration of ``option`` for ``handler``: its own value if it declares one, otherwise the value
    of the closest layer above it that declares one.
    """
    own, inherited = (
        (handler._dto, handler._inherited_dto)
        if option == "dto"
        else (handler._return_dto, handler._inherited_return_dto)
    )
    if own is not Empty:
        return DTODeclaration(option=option, value=own, source="handler")
    if inherited is not Empty:
        return DTODeclaration(option=option, value=inherited, source="layer")
    return DTODeclaration(option=option, value=Empty, source=None)


def create_backend(
    dto: type[AbstractDTO[Any]],
    field_definition: FieldDefinition,
    *,
    is_data_field: bool,
    handler_id: str,
    backend_cls: type[DTOBackend] | None = None,
    registry: TransferModelRegistry | None = None,
    name_scope: Hashable | None = None,
) -> DTOBackend:
    """Create the backend of ``dto`` for ``field_definition``, the data a handler receives if ``is_data_field``,
    otherwise the data it returns. Every backend of a plan is created here.

    The backend names its transfer models in ``registry`` under ``name_scope``, which are given together; without
    them it names them in a registry of its own.

    Raises:
        InvalidAnnotationException: If ``dto`` cannot be applied to ``field_definition``
        TypeError: If only one of ``registry`` and ``name_scope`` is given
    """
    if (registry is None) != (name_scope is None):
        raise TypeError("create_backend() takes both 'registry' and 'name_scope', or neither")

    model_type_field_definition = dto.resolve_model_type(field_definition=field_definition)
    model_type = dto.model_type  # pyright: ignore[reportGeneralTypeIssues]
    wrapper_attribute_name: str | None = None

    if not model_type_field_definition.is_subclass_of(model_type):
        if resolved_generic_result := dto.resolve_generic_wrapper_type(field_definition=model_type_field_definition):
            model_type_field_definition, field_definition, wrapper_attribute_name = resolved_generic_result
        else:
            raise InvalidAnnotationException(
                f"DTO narrowed with '{model_type}', handler type is '{field_definition.annotation}'"
            )

    if backend_cls is None:
        backend_cls = DTOBackend

    backend = backend_cls.__new__(backend_cls)
    if registry is not None:
        backend._naming = TransferModelNaming(registry, name_scope)
    backend_cls.__init__(
        backend,
        dto_factory=dto,
        field_definition=field_definition,
        model_type=model_type_field_definition.annotation,
        wrapper_attribute_name=wrapper_attribute_name,
        is_data_field=is_data_field,
        handler_id=handler_id,
    )
    return backend


def build_schema_annotation(dto: type[AbstractDTO[Any]], backend: DTOBackend, field_definition: FieldDefinition) -> Any:
    """Return the annotation to document ``field_definition`` with: the backend's annotation, or, for a model
    wrapped in a generic type other than a ``Response``, the outer generic type with the model replaced by the
    transfer model.
    """
    if backend.wrapper_attribute_name and not field_definition.is_subclass_of(Response):
        model_type = dto.model_type  # pyright: ignore[reportGeneralTypeIssues]
        generic_args = tuple(backend.transfer_model_type if arg is model_type else arg for arg in field_definition.args)
        return field_definition.safe_generic_origin[generic_args]
    return backend.annotation


@dataclass(slots=True)
class _PlanBuild:
    dto: type[AbstractDTO[Any]]
    is_data_field: bool
    backend: DTOBackend | None = None
    registry: TransferModelRegistry | None = None
    name_scope: Hashable | None = None


_plan_build: ContextVar[_PlanBuild | None] = ContextVar("_plan_build", default=None)


def take_plan_build(dto: type[AbstractDTO[Any]]) -> _PlanBuild | None:
    """Return the plan build in progress for ``dto`` and end it, so that a further call sees none."""
    build = _plan_build.get()
    if build is None or build.dto is not dto:
        return None
    _plan_build.set(None)
    return build


def build_dto_plan(handler: BaseRouteHandler, app: Litestar) -> DTOPlan:
    """Resolve the DTOs of ``handler`` from its configuration and the serialization plugins of ``app``, and build
    their backends. It reads the handler and does not modify it; a second call returns an independent plan.

    Raises:
        DTOFactoryException: If a DTO cannot be applied, with the message prefixed by the handler's paths and name
        MissingDTOError: If the handler's data is annotated with ``DTOData`` and no DTO decodes it
    """
    with HandlerErrorPrefix.for_handler(handler).wrap_dto_exception():
        data_dto = _resolve_data_dto(handler, app)
        data: DTODirectionPlan | None = None
        data_field = handler.parsed_data_field
        if data_field and data_dto:
            data = _build_direction(
                data_dto, data_field, is_data_field=True, handler=handler, registry=app._transfer_model_registry
            )
        if data is None and data_field is not None and data_field.is_subclass_of(DTOData):
            raise MissingDTOError(handler_name=handler.handler_name, annotation=data_field.annotation)

        return_: DTODirectionPlan | None = None
        return_field = handler.parsed_return_field
        candidate = _resolve_return_dto(handler, app, data_dto)
        if candidate and candidate.is_supported_model_type_field(return_field):
            return_ = _build_direction(
                candidate, return_field, is_data_field=False, handler=handler, registry=app._transfer_model_registry
            )

        return DTOPlan(
            data=data,
            return_=return_,
            data_dto=data_dto,
            decode_bytes=(
                _create_decoder(data.dto, "decode_bytes", data.backend.populate_data_from_raw) if data else None
            ),
            decode_builtins=(
                _create_decoder(data.dto, "decode_builtins", data.backend.populate_data_from_builtins) if data else None
            ),
            encode=_create_encoder(return_.dto, return_.backend) if return_ else None,
        )


def _create_decoder(
    dto: type[AbstractDTO[Any]], name: Literal["decode_bytes", "decode_builtins"], backend_method: DecodeFn
) -> DecodeFn:
    if not dto._overrides(name):
        return dto._wrap_decoder(backend_method)
    if name == "decode_bytes":
        return lambda value, connection: dto(connection).decode_bytes(value)
    return lambda value, connection: dto(connection).decode_builtins(value)


def _create_encoder(dto: type[AbstractDTO[Any]], backend: DTOBackend) -> EncodeFn:
    if dto._overrides("data_to_encodable_type"):
        return lambda data, connection: dto(connection).data_to_encodable_type(data)

    encode_data = backend.encode_data

    def encode(data: Any, connection: ASGIConnection[Any, Any, Any, Any]) -> LitestarEncodableType:
        return encode_data(data)

    return encode


def _find_serialization_plugin(app: Litestar, field_definition: FieldDefinition) -> SerializationPlugin | None:
    return next(
        (
            plugin
            for plugin in app.plugins.serialization
            if field_definition.match_predicate_recursively(plugin.supports_type)
        ),
        None,
    )


def _resolve_data_dto(handler: BaseRouteHandler, app: Litestar) -> type[AbstractDTO[Any]] | None:
    if (configured := read_dto_declaration(handler, "dto").value) is not Empty:
        return configured
    if (data_field := handler.parsed_data_field) and (plugin := _find_serialization_plugin(app, data_field)):
        return plugin.create_dto_for_type(data_field)
    return None


def _resolve_return_dto(
    handler: BaseRouteHandler, app: Litestar, data_dto: type[AbstractDTO[Any]] | None
) -> type[AbstractDTO[Any]] | None:
    return_field = handler.parsed_return_field
    if (configured := read_dto_declaration(handler, "return_dto").value) is not Empty:
        return configured
    if data_dto is not None and data_dto.is_supported_model_type_field(return_field):
        return data_dto
    if plugin := _find_serialization_plugin(app, return_field):
        return plugin.create_dto_for_type(return_field)
    return data_dto


def _build_direction(
    dto: type[AbstractDTO[Any]],
    field_definition: FieldDefinition,
    *,
    is_data_field: bool,
    handler: BaseRouteHandler,
    registry: TransferModelRegistry,
) -> DTODirectionPlan:
    name_scope = handler_name_scope(handler)
    if not dto._overrides("create_for_field_definition"):
        backend = create_backend(
            dto,
            field_definition,
            is_data_field=is_data_field,
            handler_id=str(handler.handler_id),
            registry=registry,
            name_scope=name_scope,
        )
    else:
        build = _PlanBuild(dto=dto, is_data_field=is_data_field, registry=registry, name_scope=name_scope)
        field = field_definition
        if is_data_field and not isinstance(field_definition.kwarg_definition, BodyKwarg):
            field = dataclasses.replace(field_definition, kwarg_definition=BodyKwarg())
        token = _plan_build.set(build)
        try:
            dto.create_for_field_definition(field_definition=field, handler_id=handler.handler_id)
        except AttributeError as exc:
            if exc.name != "_dto_backends":
                raise
            raise _no_backend_error(dto, handler) from exc
        finally:
            _plan_build.reset(token)
        if build.backend is None:
            raise _no_backend_error(dto, handler)
        backend = build.backend

    backend._bind_handler(type_decoders=handler.type_decoders, default_deserializer=handler.default_deserializer)
    return DTODirectionPlan(
        dto=dto, backend=backend, schema_annotation=build_schema_annotation(dto, backend, field_definition)
    )


def dto_name(dto: type[AbstractDTO[Any]]) -> str:
    """Name ``dto`` in an error message."""
    return getattr(dto, "__qualname__", repr(dto))


def _no_backend_error(dto: type[AbstractDTO[Any]], handler: BaseRouteHandler) -> DTOFactoryException:
    return DTOFactoryException(
        f"{dto_name(dto)}.create_for_field_definition() created no backend for handler {handler}: an override must "
        "call the base method"
    )


def create_dto_openapi_schema(
    direction: DTODirectionPlan,
    field_definition: FieldDefinition,
    handler: BaseRouteHandler,
    schema_creator: SchemaCreator,
) -> Reference | Schema:
    """Return the OpenAPI schema of ``field_definition``, the handler's own field in ``direction``. A DTO class that
    overrides ``create_openapi_schema`` is called through it.
    """
    dto = direction.dto
    if dto._overrides("create_openapi_schema"):
        return dto.create_openapi_schema(
            field_definition=field_definition, handler_id=handler.handler_id, schema_creator=schema_creator
        )
    try:
        return schema_creator.for_field_definition(
            FieldDefinition.from_annotation(
                direction.schema_annotation, kwarg_definition=field_definition.kwarg_definition
            )
        )
    except TypeError as exc:
        with HandlerErrorPrefix.for_handler(handler).wrap_dto_exception():
            try:
                msgspec.json.Decoder(direction.backend.annotation, strict=False)
            except TypeError as decoder_exc:
                raise DTOTransferTypeError(
                    f"msgspec cannot describe the transfer model of {_qualified_name(direction.backend.model_type)!r}: "
                    f"{exc}"
                ) from decoder_exc
        raise
