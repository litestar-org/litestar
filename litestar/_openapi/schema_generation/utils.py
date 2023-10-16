from __future__ import annotations

from typing import Any

from typing_extensions import get_type_hints

from litestar.openapi.spec import Reference, Schema
from litestar.utils.predicates import is_generic
from litestar.utils.typing import get_origin_or_inner_type, get_type_hints_with_generics_resolved

__all__ = ("sort_schemas_and_references",)


def sort_schemas_and_references(values: list[Schema | Reference]) -> list[Schema | Reference]:
    """Sort schemas and references alphabetically

    Args:
        values: A list of schemas or references.

    Returns:
        A sorted list of schemas or references
    """
    return sorted(values, key=lambda value: value.type if isinstance(value, Schema) else value.ref)  # type: ignore


def get_unwrapped_annotation_and_type_hints(annotation: Any) -> tuple[Any, dict[str, Any]]:
    """Get the unwrapped annotation and the type hints after resolving generics.

    Args:
        annotation: A type annotation.

    Returns:
        A tuple containing the unwrapped annotation and the type hints.
    """

    if is_generic(annotation):
        origin = get_origin_or_inner_type(annotation)
        return origin or annotation, get_type_hints_with_generics_resolved(annotation, include_extras=True)
    return annotation, get_type_hints(annotation, include_extras=True)
