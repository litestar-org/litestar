from __future__ import annotations

from litestar.openapi.spec import Reference, Schema

__all__ = ("sort_schemas_and_references",)


def sort_schemas_and_references(values: list[Schema | Reference]) -> list[Schema | Reference]:
    """Sort schemas and references alphabetically

    Args:
        values: A list of schemas or references.

    Returns:
        A sorted list of schemas or references
    """
    return sorted(values, key=lambda value: value.type if isinstance(value, Schema) else value.ref)  # type: ignore
