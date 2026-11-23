import dataclasses
from contextvars import ContextVar
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

from litestar.dto._backend import DTOBackend
from litestar.exceptions.dto_exceptions import DTOFactoryException, InvalidAnnotationException
from litestar.params import BodyKwarg
from litestar.response.base import Response
from litestar.types import Empty
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.app import Litestar
    from litestar.connection import ASGIConnection
    from litestar.dto.base_dto import AbstractDTO
    from litestar.handlers.base import BaseRouteHandler
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType

__all__ = (
    "DTODirectionPlan",
    "DTOPlan",
    "DecodeFn",
    "EncodeFn",
    "build_dto_plan",
    "build_schema_annotation",
    "create_backend",
    "create_dto_openapi_schema",
    "get_direction_plan",
)

DecodeFn: TypeAlias = "Callable[[Any, ASGIConnection[Any, Any, Any, Any]], Any]"
EncodeFn: TypeAlias = "Callable[[Any, ASGIConnection[Any, Any, Any, Any]], LitestarEncodableType]"


@dataclass(frozen=True, slots=True)
class DTODirectionPlan:
    dto: "type[AbstractDTO[Any]]"
    backend: DTOBackend
    schema_annotation: Any


@dataclass(frozen=True, slots=True)
class DTOPlan:
    data: DTODirectionPlan | None
    return_: DTODirectionPlan | None
    data_dto: "type[AbstractDTO[Any]] | None"
    decode_bytes: "DecodeFn | None" = None
    decode_builtins: "DecodeFn | None" = None
    encode: "EncodeFn | None" = None


def create_backend(
    dto: "type[AbstractDTO[Any]]",
    field_definition: FieldDefinition,
    *,
    is_data_field: bool,
    handler_id: str,
    backend_cls: type[DTOBackend] | None = None,
) -> DTOBackend:
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

    return backend_cls(
        dto_factory=dto,
        field_definition=field_definition,
        model_type=model_type_field_definition.annotation,
        wrapper_attribute_name=wrapper_attribute_name,
        is_data_field=is_data_field,
        handler_id=handler_id,
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


@dataclass(slots=True)
class _PlanBuild:
    dto: "type[AbstractDTO[Any]]"
    is_data_field: bool
    backend: DTOBackend | None = None


_plan_build: ContextVar[_PlanBuild | None] = ContextVar("_plan_build", default=None)


def build_dto_plan(handler: "BaseRouteHandler", app: "Litestar") -> DTOPlan:
    data_dto = _resolve_data_dto(handler, app)
    data: DTODirectionPlan | None = None
    if (data_field := handler.parsed_data_field) and data_dto:
        data = _build_direction(data_dto, data_field, is_data_field=True, handler=handler)

    return_: DTODirectionPlan | None = None
    return_field = handler.parsed_return_field
    candidate = _resolve_return_dto(handler, app, data_dto)
    if candidate and candidate.is_supported_model_type_field(return_field):
        return_ = _build_direction(candidate, return_field, is_data_field=False, handler=handler)

    return DTOPlan(
        data=data,
        return_=return_,
        data_dto=data_dto,
        decode_bytes=_create_decoder(data.dto, "decode_bytes", data.backend.populate_data_from_raw) if data else None,
        decode_builtins=(
            _create_decoder(data.dto, "decode_builtins", data.backend.populate_data_from_builtins) if data else None
        ),
        encode=_create_encoder(return_.dto, return_.backend) if return_ else None,
    )


def _create_decoder(
    dto: "type[AbstractDTO[Any]]", name: Literal["decode_bytes", "decode_builtins"], backend_method: DecodeFn
) -> DecodeFn:
    from litestar.dto.base_dto import AbstractDTO

    if getattr(dto, name) is getattr(AbstractDTO, name):
        return dto._wrap_decoder(backend_method)
    if name == "decode_bytes":
        return lambda value, connection: dto(connection).decode_bytes(value)
    return lambda value, connection: dto(connection).decode_builtins(value)


def _create_encoder(dto: "type[AbstractDTO[Any]]", backend: DTOBackend) -> EncodeFn:
    from litestar.dto.base_dto import AbstractDTO

    if dto.data_to_encodable_type is not AbstractDTO.data_to_encodable_type:
        return lambda data, connection: dto(connection).data_to_encodable_type(data)

    encode_data = backend.encode_data

    def encode(data: Any, connection: "ASGIConnection[Any, Any, Any, Any]") -> "LitestarEncodableType":
        return encode_data(data)

    return encode


def _resolve_data_dto(handler: "BaseRouteHandler", app: "Litestar") -> "type[AbstractDTO[Any]] | None":
    if (configured := handler._dto) is not Empty:
        return configured
    if (data_field := handler.parsed_data_field) and (
        plugin := next(
            (
                plugin
                for plugin in app.plugins.serialization
                if data_field.match_predicate_recursively(plugin.supports_type)
            ),
            None,
        )
    ):
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
    if plugin := next(
        (
            plugin
            for plugin in app.plugins.serialization
            if return_field.match_predicate_recursively(plugin.supports_type)
        ),
        None,
    ):
        return plugin.create_dto_for_type(return_field)
    return data_dto


def _build_direction(
    dto: "type[AbstractDTO[Any]]",
    field_definition: FieldDefinition,
    *,
    is_data_field: bool,
    handler: "BaseRouteHandler",
) -> DTODirectionPlan:
    from litestar.dto.base_dto import AbstractDTO

    if (
        getattr(dto.create_for_field_definition, "__func__", None)
        is vars(AbstractDTO)["create_for_field_definition"].__func__
    ):
        backend = create_backend(dto, field_definition, is_data_field=is_data_field, handler_id=str(handler.handler_id))
    else:
        build = _PlanBuild(dto=dto, is_data_field=is_data_field)
        field = field_definition
        if is_data_field and not isinstance(field_definition.kwarg_definition, BodyKwarg):
            field = dataclasses.replace(field_definition, kwarg_definition=BodyKwarg())
        token = _plan_build.set(build)
        try:
            dto.create_for_field_definition(field_definition=field, handler_id=handler.handler_id)
        finally:
            _plan_build.reset(token)
        if build.backend is None:
            raise DTOFactoryException(
                f"{getattr(dto, '__qualname__', repr(dto))}.create_for_field_definition() created no backend for handler {handler}: an override "
                "must call the base method"
            )
        backend = build.backend

    backend._bind_handler(type_decoders=handler.type_decoders, default_deserializer=handler.default_deserializer)
    return DTODirectionPlan(
        dto=dto, backend=backend, schema_annotation=build_schema_annotation(dto, backend, field_definition)
    )


def get_direction_plan(
    handler: "BaseRouteHandler | None", *, is_data_field: bool, dto: "type[AbstractDTO[Any]] | None" = None
) -> DTODirectionPlan:
    if handler is not None:
        if (plan := handler._dto_plan) is not None:
            if (direction := plan.data if is_data_field else plan.return_) is not None:
                return direction
        elif dto is not None and (direction := _direct_direction(dto, handler.handler_id, is_data_field)):
            return direction
    raise DTOFactoryException(f"Handler {handler} has no {'data' if is_data_field else 'return'} DTO")


def _direct_direction(dto: "type[AbstractDTO[Any]]", handler_id: str, is_data_field: bool) -> DTODirectionPlan | None:
    from litestar.dto.base_dto import _get_direct_backend

    if (backend := _get_direct_backend(dto, handler_id, is_data_field)) is None:
        return None
    return DTODirectionPlan(dto=dto, backend=backend, schema_annotation=backend.annotation)


def create_dto_openapi_schema(
    direction: DTODirectionPlan,
    field_definition: FieldDefinition,
    handler: "BaseRouteHandler",
    schema_creator: "SchemaCreator",
) -> "Reference | Schema":
    from litestar.dto.base_dto import AbstractDTO

    dto = direction.dto
    if getattr(dto.create_openapi_schema, "__func__", None) is not vars(AbstractDTO)["create_openapi_schema"].__func__:
        return dto.create_openapi_schema(
            field_definition=field_definition, handler_id=handler.handler_id, schema_creator=schema_creator
        )
    return schema_creator.for_field_definition(
        FieldDefinition.from_annotation(direction.schema_annotation, kwarg_definition=field_definition.kwarg_definition)
    )
