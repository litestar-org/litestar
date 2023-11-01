from __future__ import annotations

import re

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


TYPE_NAME_NORMALIZATION_REGEX = re.compile(r"[^a-zA-Z0-9_]")


def normalize_type_name(type_annotation_str: str) -> str:
    """Normalize a type annotation, replacing all non-alphanumeric with underscores. Existing underscores will be left as-is

    Args:
        type_annotation_str (str): A string representing a type annotation (i.e. 'typing.Dict[str, typing.Any]' or '<class 'model.Foo'>')

    Returns:
        str: A normalized version of the input string
    """
    # Use a regular expression to replace non-alphanumeric characters with underscores
    return re.sub(TYPE_NAME_NORMALIZATION_REGEX, "_", type_annotation_str)
