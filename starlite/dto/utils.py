from __future__ import annotations

from collections.abc import Iterable as CollectionsIterable
from inspect import getmodule
from typing import TYPE_CHECKING, TypeVar

from msgspec import Struct
from typing_extensions import get_args, get_origin, get_type_hints

from .config import DTOConfig
from .exc import InvalidAnnotation
from .types import NestedFieldDefinition

if TYPE_CHECKING:
    from typing import Any, Iterable

    from .types import FieldDefinitionsType

__all__ = (
    "build_data_from_struct",
    "build_struct_from_model",
    "get_model_type_hints",
    "parse_config_from_annotated",
)

T = TypeVar("T")
StructT = TypeVar("StructT", bound="Struct")


def get_model_type_hints(model_type: type[Any]) -> dict[str, Any]:
    """Retrieve type annotations for ``model_type``.

    Args:
        model_type: Any type-annotated class.

    Returns:
        Type hints for ``model_type`` resolved within the scope of its module.
    """
    model_module = getmodule(model_type)
    localns = vars(model_module) if model_module is not None else {}
    return get_type_hints(model_type, localns=localns)


def parse_config_from_annotated(item: Any) -> tuple[type[Any], DTOConfig]:
    """Extract data type and config instance from ``Annotated`` annotation.

    Args:
        item: ``Annotated`` type hint

    Returns:
        The type and config object extracted from the annotation.
    """
    item, expected_config, *_ = get_args(item)
    if not isinstance(expected_config, DTOConfig):
        raise InvalidAnnotation("Annotation metadata must be an instance of `DTOConfig`.")
    return item, expected_config


def build_data_from_struct(
    model_type: type[T], data: Struct | Iterable[Struct], field_definitions: FieldDefinitionsType
) -> T | Iterable[T]:
    """Create instance or iterable of instances of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``annotation``.
    """
    if isinstance(data, CollectionsIterable):
        return type(data)(  # type:ignore[return-value]
            build_data_from_struct(model_type, item, field_definitions) for item in data  # type:ignore[call-arg]
        )

    unstructured_data = {}
    for k in data.__slots__:  # type:ignore[attr-defined]
        v = getattr(data, k)

        field_definition = field_definitions[k]

        if isinstance(field_definition, NestedFieldDefinition) and isinstance(v, CollectionsIterable):
            if field_definition.origin is None:  # pragma: no cover
                raise RuntimeError("Unexpected origin value for collection type.")
            unstructured_data[k] = field_definition.origin(
                build_data_from_struct(field_definition.nested_type, item, field_definition.nested_field_definitions)
                for item in v
            )
        elif isinstance(field_definition, NestedFieldDefinition):
            unstructured_data[k] = build_data_from_struct(
                field_definition.nested_type, v, field_definition.nested_field_definitions
            )
        else:
            unstructured_data[k] = v

    return model_type(**unstructured_data)


def build_struct_from_model(model: Any, struct_type: type[StructT]) -> StructT:
    """Convert ``model`` to instance of ``struct_type``

    It is expected that attributes of ``struct_type`` are a subset of the attributes of ``model``.

    Args:
        model: a model instance
        struct_type: a subclass of ``msgspec.Struct``

    Returns:
        Instance of ``struct_type``.
    """
    data = {}
    struct_type_annotations = get_type_hints(struct_type)
    for key, type_ in struct_type_annotations.items():
        model_val = getattr(model, key)
        if issubclass(type_, Struct):
            data[key] = build_struct_from_model(model_val, type_)
        elif issubclass(origin := (get_origin(type_) or type_), CollectionsIterable):
            args = get_args(type_)
            if args and issubclass(args[0], Struct):
                data[key] = origin(build_struct_from_model(m, args[0]) for m in model_val)  # pyright:ignore
            else:
                data[key] = model_val
        else:
            data[key] = model_val
    return struct_type(**data)
