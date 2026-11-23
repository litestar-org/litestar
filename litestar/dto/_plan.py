from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeAlias

from litestar.dto._backend import DTOBackend
from litestar.exceptions.dto_exceptions import InvalidAnnotationException
from litestar.response.base import Response

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.connection import ASGIConnection
    from litestar.dto.base_dto import AbstractDTO
    from litestar.types.serialization import LitestarEncodableType
    from litestar.typing import FieldDefinition

__all__ = (
    "DTODirectionPlan",
    "DTOPlan",
    "DecodeFn",
    "EncodeFn",
    "build_schema_annotation",
    "create_backend",
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
    field_definition: "FieldDefinition",
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
    dto: "type[AbstractDTO[Any]]", backend: DTOBackend, field_definition: "FieldDefinition"
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
