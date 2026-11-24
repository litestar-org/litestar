from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias

from litestar.dto._backend import DTOBackend
from litestar.dto._registry import TransferModelNaming
from litestar.exceptions.dto_exceptions import InvalidAnnotationException
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
    from litestar.types.serialization import LitestarEncodableType

__all__ = (
    "DTOPlan",
    "DecodeFn",
    "EncodeFn",
    "build_dto_plan",
    "build_schema_annotation",
    "create_backend",
    "create_dto_openapi_schema",
    "dto_name",
)

DecodeFn: TypeAlias = "Callable[[Any, ASGIConnection[Any, Any, Any, Any]], Any]"
EncodeFn: TypeAlias = "Callable[[Any], LitestarEncodableType]"


@dataclass(frozen=True, slots=True)
class DTODirectionPlan:
    """How a route handler applies a DTO in one direction, to the data it receives or to the data it returns."""

    dto: "type[AbstractDTO[Any]]"
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
    data_dto: "type[AbstractDTO[Any]] | None"
    """The resolved data DTO class. It may be set while :attr:`data` is ``None``, for a handler configured with a
    ``dto`` that receives no data
    """
    decode_bytes: "DecodeFn | None"
    """Decode raw request data with the data DTO. Set exactly when :attr:`data` is set"""
    decode_builtins: "DecodeFn | None"
    """Decode builtin values, such as form data, with the data DTO. Set exactly when :attr:`data` is set"""
    encode: "EncodeFn | None"
    """Encode returned data with the return DTO. Set exactly when :attr:`return_` is set"""


def create_backend(
    dto: "type[AbstractDTO[Any]]",
    field_definition: FieldDefinition,
    *,
    is_data_field: bool,
    handler_id: str,
    backend_cls: type[DTOBackend] | None = None,
    naming: TransferModelNaming | None = None,
) -> DTOBackend:
    """Create the backend of ``dto`` for ``field_definition``, the data a handler receives if ``is_data_field``,
    otherwise the data it returns. Every backend of a plan is created here.

    The backend names its transfer models through ``naming``, or, without it, in a registry of its own.

    Raises:
        InvalidAnnotationException: If ``dto`` cannot be applied to ``field_definition``
    """
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

    keywords: dict[str, Any] = {"naming": naming} if naming is not None else {}
    return backend_cls(
        dto_factory=dto,
        field_definition=field_definition,
        model_type=model_type_field_definition.annotation,
        wrapper_attribute_name=wrapper_attribute_name,
        is_data_field=is_data_field,
        handler_id=handler_id,
        **keywords,
    )


def build_schema_annotation(
    dto: "type[AbstractDTO[Any]]", backend: DTOBackend, field_definition: FieldDefinition
) -> Any:
    """Return the annotation to document ``field_definition`` with: the backend's annotation, or, for a model
    wrapped in a generic type other than a ``Response``, the outer generic type with the model replaced by the
    transfer model.
    """
    if backend.wrapper_attribute_name and not field_definition.is_subclass_of(Response):
        model_type = dto.model_type  # pyright: ignore[reportGeneralTypeIssues]
        generic_args = tuple(backend.transfer_model_type if arg is model_type else arg for arg in field_definition.args)
        return field_definition.safe_generic_origin[generic_args]
    return backend.annotation


def handler_name_scope(handler: "BaseRouteHandler") -> "Hashable":
    """Return the value that identifies ``handler`` for naming, equal for every merge of the same registration."""
    return (
        str(handler),
        type(handler).__qualname__,
        tuple(sorted(handler.paths)),
        tuple(sorted(getattr(handler, "http_methods", ()))),
    )


def build_dto_plan(handler: "BaseRouteHandler", app: "Litestar") -> DTOPlan:
    """Resolve the DTOs of ``handler`` from its configuration and the serialization plugins of ``app``, and build
    their backends. It reads the handler and does not modify it; a second call returns an independent plan.
    """
    registry = app._transfer_model_registry
    name_scope = handler_name_scope(handler)
    data_dto = _resolve_data_dto(handler, app)
    data: DTODirectionPlan | None = None
    if (data_field := handler.parsed_data_field) and data_dto:
        data = _build_direction(
            data_dto, data_field, is_data_field=True, handler=handler, naming=TransferModelNaming(registry, name_scope)
        )

    return_: DTODirectionPlan | None = None
    return_field = handler.parsed_return_field
    candidate = _resolve_return_dto(handler, app, data_dto)
    if candidate and candidate.is_supported_model_type_field(return_field):
        return_ = _build_direction(
            candidate,
            return_field,
            is_data_field=False,
            handler=handler,
            naming=TransferModelNaming(registry, name_scope),
        )

    return DTOPlan(
        data=data,
        return_=return_,
        data_dto=data_dto,
        decode_bytes=data.dto._wrap_decoder(data.backend.populate_data_from_raw) if data else None,
        decode_builtins=data.dto._wrap_decoder(data.backend.populate_data_from_builtins) if data else None,
        encode=return_.backend.encode_data if return_ else None,
    )


def _find_serialization_plugin(app: "Litestar", field_definition: FieldDefinition) -> "SerializationPlugin | None":
    return next(
        (
            plugin
            for plugin in app.plugins.serialization
            if field_definition.match_predicate_recursively(plugin.supports_type)
        ),
        None,
    )


def _resolve_data_dto(handler: "BaseRouteHandler", app: "Litestar") -> "type[AbstractDTO[Any]] | None":
    if (configured := handler._dto) is not Empty:
        return configured
    if (data_field := handler.parsed_data_field) and (plugin := _find_serialization_plugin(app, data_field)):
        return plugin.create_dto_for_type(data_field)
    return None


def _resolve_return_dto(
    handler: "BaseRouteHandler", app: "Litestar", data_dto: "type[AbstractDTO[Any]] | None"
) -> "type[AbstractDTO[Any]] | None":
    return_field = handler.parsed_return_field
    if (configured := handler._return_dto) is not Empty:
        return configured
    if data_dto is not None and data_dto.is_supported_model_type_field(return_field):
        return data_dto
    if plugin := _find_serialization_plugin(app, return_field):
        return plugin.create_dto_for_type(return_field)
    return data_dto


def _build_direction(
    dto: "type[AbstractDTO[Any]]",
    field_definition: FieldDefinition,
    *,
    is_data_field: bool,
    handler: "BaseRouteHandler",
    naming: TransferModelNaming,
) -> DTODirectionPlan:
    backend = create_backend(
        dto,
        field_definition,
        is_data_field=is_data_field,
        handler_id=handler.handler_id,
        naming=naming,
    )
    backend._bind_handler(type_decoders=handler.type_decoders, default_deserializer=handler.default_deserializer)
    return DTODirectionPlan(
        dto=dto,
        backend=backend,
        schema_annotation=build_schema_annotation(dto, backend, field_definition),
    )


def dto_name(dto: "type[AbstractDTO[Any]]") -> str:
    """Name ``dto`` in an error message."""
    return getattr(dto, "__qualname__", repr(dto))


def create_dto_openapi_schema(
    direction: DTODirectionPlan,
    field_definition: FieldDefinition,
    schema_creator: "SchemaCreator",
) -> "Reference | Schema":
    """Return the OpenAPI schema of ``field_definition``, the handler's own field in ``direction``."""
    return schema_creator.for_field_definition(
        FieldDefinition.from_annotation(direction.schema_annotation, kwarg_definition=field_definition.kwarg_definition)
    )
