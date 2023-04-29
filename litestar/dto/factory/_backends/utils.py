from __future__ import annotations

from typing import TYPE_CHECKING, TypeVar

from typing_extensions import get_origin

from litestar.dto.factory.types import FieldDefinition, FieldDefinitionsType, NestedFieldDefinition

if TYPE_CHECKING:
    from typing import Any, Iterable

__all__ = ("build_annotation_for_backend",)

T = TypeVar("T")


def build_annotation_for_backend(annotation: Any, model: type[T]) -> type[T] | type[Iterable[T]]:
    """A helper to re-build a generic outer type with new inner type.

    Args:
        annotation: The original annotation on the handler signature
        model: The data container type

    Returns:
        Annotation with new inner type if applicable.
    """
    origin = get_origin(annotation)
    if not origin:
        return model
    try:
        return origin[model]  # type:ignore[no-any-return]
    except TypeError:  # pragma: no cover
        return annotation.copy_with((model,))  # type:ignore[no-any-return]


def generate_reverse_name_map(field_definitions: FieldDefinitionsType) -> dict[str, str]:
    result = {}
    for field_definition in field_definitions.values():
        result.update(_generate_reverse_name_map(field_definition))

    return result


def _generate_reverse_name_map(field_definition: FieldDefinition | NestedFieldDefinition) -> dict[str, str]:
    if isinstance(field_definition, FieldDefinition):
        return (
            {field_definition.serialization_name: field_definition.name} if field_definition.serialization_name else {}
        )

    return generate_reverse_name_map(field_definition.nested_field_definitions)
