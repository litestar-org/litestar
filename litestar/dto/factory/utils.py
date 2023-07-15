from __future__ import annotations

import typing
from inspect import getmodule
from typing import TYPE_CHECKING, TypeVar

from msgspec import Struct
from typing_extensions import get_type_hints

from litestar.types.builtin_types import NoneType
from litestar.types.composite_types import TypeEncodersMap
from litestar.typing import FieldDefinition

from .config import DTOConfig
from .data_structures import DTOData

if TYPE_CHECKING:
    from typing import Any

__all__ = (
    "get_model_type_hints",
    "get_dto_config_from_annotated_type",
    "resolve_generic_wrapper_type",
    "resolve_model_type",
)

T = TypeVar("T")
StructT = TypeVar("StructT", bound=Struct)


def get_model_type_hints(model_type: type[Any], namespace: dict[str, Any] | None = None) -> dict[str, FieldDefinition]:
    """Retrieve type annotations for ``model_type``.

    Args:
        model_type: Any type-annotated class.
        namespace: Optional namespace to use for resolving type hints.

    Returns:
        Parsed type hints for ``model_type`` resolved within the scope of its module.
    """
    namespace = namespace or {}
    namespace.update(vars(typing))
    namespace.update({"TypeEncodersMap": TypeEncodersMap})

    if model_module := getmodule(model_type):
        namespace.update(vars(model_module))

    return {
        k: FieldDefinition.from_kwarg(annotation=v, name=k)
        for k, v in get_type_hints(model_type, localns=namespace, include_extras=True).items()
    }


def get_dto_config_from_annotated_type(field_definition: FieldDefinition) -> DTOConfig | None:
    """Extract data type and config instances from ``Annotated`` annotation.

    Args:
        field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.

    Returns:
        The type and config object extracted from the annotation.
    """
    if configs := [item for item in field_definition.metadata if isinstance(item, DTOConfig)]:
        return configs[0]
    return None


def resolve_model_type(field_definition: FieldDefinition) -> FieldDefinition:
    """Resolve the data model type from a parsed type.

    Args:
        field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.

    Returns:
        A :class:`FieldDefinition <.typing.FieldDefinition>` that represents the data model type.
    """
    if field_definition.is_optional:
        return resolve_model_type(next(t for t in field_definition.inner_types if not t.is_subclass_of(NoneType)))

    if field_definition.is_subclass_of(DTOData):
        return resolve_model_type(field_definition.inner_types[0])

    if field_definition.is_collection:
        if field_definition.is_mapping:
            return resolve_model_type(field_definition.inner_types[1])

        if field_definition.is_tuple:
            if any(t is Ellipsis for t in field_definition.args):
                return resolve_model_type(field_definition.inner_types[0])
        elif field_definition.is_non_string_collection:
            return resolve_model_type(field_definition.inner_types[0])

    return field_definition


def resolve_generic_wrapper_type(
    field_definition: FieldDefinition, dto_specialized_type: type[Any]
) -> tuple[FieldDefinition, FieldDefinition, str] | None:
    """Handle where DTO supported data is wrapped in a generic container type.

    Args:
        field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.
        dto_specialized_type: The type used to specialize the DTO.

    Returns:
        The data model type.
    """
    if not (origin := field_definition.origin):
        return None

    if not (parameters := getattr(origin, "__parameters__", None)):
        return None  # pragma: no cover

    for param_index, inner_type in enumerate(field_definition.inner_types):  # noqa: B007 (`param_index` not used)
        model_type = resolve_model_type(inner_type)
        if model_type.is_subclass_of(dto_specialized_type):
            break
    else:
        return None

    type_var = parameters[param_index]
    for attr, attr_type in get_model_type_hints(origin).items():
        if attr_type.annotation is type_var or any(t.annotation is type_var for t in attr_type.inner_types):
            if attr_type.is_non_string_collection:
                # the inner type of the collection type is the type var, so we need to specialize the
                # collection type with the DTO supported type.
                specialized_annotation = attr_type.safe_generic_origin[model_type.annotation]
                return model_type, FieldDefinition.from_annotation(specialized_annotation), attr
            return model_type, inner_type, attr

    return None
