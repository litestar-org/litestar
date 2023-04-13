from __future__ import annotations

from collections.abc import Iterable as CollectionsIterable
from inspect import getmodule
from typing import TYPE_CHECKING, TypeVar

from msgspec import Struct
from typing_extensions import get_type_hints

from litestar.utils.signature import ParsedType
from litestar.utils.typing import unwrap_annotation

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
StructT = TypeVar("StructT", bound=Struct)


def get_model_type_hints(model_type: type[Any], namespace: dict[str, Any] | None = None) -> dict[str, ParsedType]:
    """Retrieve type annotations for ``model_type``.

    Args:
        model_type: Any type-annotated class.
        namespace: Optional namespace to use for resolving type hints.

    Returns:
        Parsed type hints for ``model_type`` resolved within the scope of its module.
    """
    model_module = getmodule(model_type)
    localns = namespace or {}
    if model_module:
        localns.update(vars(model_module))
    return {k: ParsedType(v) for k, v in get_type_hints(model_type, localns=localns).items()}


def parse_config_from_annotated(item: Any) -> tuple[type[Any], DTOConfig]:
    """Extract data type and config instance from ``Annotated`` annotation.

    Args:
        item: ``Annotated`` type hint

    Returns:
        The type and config object extracted from the annotation.
    """
    unwrapped, meta, _ = unwrap_annotation(item)
    if not meta:
        return unwrapped, DTOConfig()
    expected_config = meta[0]
    if not isinstance(expected_config, DTOConfig):
        raise InvalidAnnotation("Annotation metadata must be an instance of `DTOConfig`.")
    return unwrapped, expected_config


def _build_data_from_struct(model_type: type[T], data: Struct, field_definitions: FieldDefinitionsType) -> T:
    """Create instance of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    unstructured_data = {}
    for k in data.__slots__:  # type:ignore[attr-defined]
        v = getattr(data, k)

        field = field_definitions[k]

        if isinstance(field, NestedFieldDefinition) and isinstance(v, CollectionsIterable):
            parsed_type = field.field_definition.parsed_type
            if parsed_type.origin is None:  # pragma: no cover
                raise RuntimeError("Unexpected origin value for collection type.")
            unstructured_data[k] = parsed_type.origin(
                _build_data_from_struct(field.nested_type, item, field.nested_field_definitions) for item in v
            )
        elif isinstance(field, NestedFieldDefinition) and isinstance(v, Struct):
            unstructured_data[k] = _build_data_from_struct(field.nested_type, v, field.nested_field_definitions)
        else:
            unstructured_data[k] = v

    return model_type(**unstructured_data)


def build_data_from_struct(
    model_type: type[T], data: Struct | Iterable[Struct], field_definitions: FieldDefinitionsType
) -> T | Iterable[T]:
    """Create instance or iterable of instances of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    if isinstance(data, CollectionsIterable):
        return type(data)(  # type:ignore[return-value]
            build_data_from_struct(model_type, item, field_definitions) for item in data  # type:ignore[call-arg]
        )
    return _build_data_from_struct(model_type, data, field_definitions)


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
    for key, parsed_type in get_model_type_hints(struct_type).items():
        model_val = getattr(model, key)
        if parsed_type.is_subclass_of(Struct):
            data[key] = build_struct_from_model(model_val, parsed_type.annotation)
        elif parsed_type.is_union and parsed_type.has_inner_subclass_of(Struct) and model_val is not None:
            for inner_type in parsed_type.inner_types:
                if inner_type.is_subclass_of(Struct):
                    try:
                        data[key] = build_struct_from_model(model_val, inner_type.annotation)
                    except TypeError:
                        continue
                    else:
                        break
        elif parsed_type.is_collection:
            if parsed_type.inner_types and (inner_type := parsed_type.inner_types[0]).is_subclass_of(Struct):
                data[key] = parsed_type.origin(build_struct_from_model(m, inner_type.annotation) for m in model_val)
            else:
                data[key] = model_val
        else:
            data[key] = model_val
    return struct_type(**data)
