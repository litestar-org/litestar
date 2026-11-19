# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

from re import Pattern
from typing import TYPE_CHECKING

from litestar.openapi.spec.enums import OpenAPIType
from litestar.openapi.spec.schema import Schema

if TYPE_CHECKING:
    from litestar.params import KwargDefinition

__all__ = (
    "create_numerical_constrained_field_schema",
    "create_string_constrained_field_schema",
)


def create_numerical_constrained_field_schema(
    field_type: type[int] | type[float],
    kwarg_definition: KwargDefinition,
) -> Schema:
    """Create Schema from Constrained Int/Float field."""
    schema = Schema(type=OpenAPIType.INTEGER if issubclass(field_type, int) else OpenAPIType.NUMBER)
    if kwarg_definition.le is not None:
        schema.maximum = float(kwarg_definition.le)
    if kwarg_definition.lt is not None:
        schema.exclusive_maximum = float(kwarg_definition.lt)
    if kwarg_definition.ge is not None:
        schema.minimum = float(kwarg_definition.ge)
    if kwarg_definition.gt is not None:
        schema.exclusive_minimum = float(kwarg_definition.gt)
    if kwarg_definition.multiple_of is not None:
        schema.multiple_of = float(kwarg_definition.multiple_of)
    return schema


def create_string_constrained_field_schema(
    field_type: type[str] | type[bytes],
    kwarg_definition: KwargDefinition,
) -> Schema:
    """Create Schema from Constrained Str/Bytes field."""
    schema = Schema(type=OpenAPIType.STRING)
    if issubclass(field_type, bytes):
        schema.content_encoding = "utf-8"
    if kwarg_definition.min_length:
        schema.min_length = kwarg_definition.min_length
    if kwarg_definition.max_length:
        schema.max_length = kwarg_definition.max_length
    if kwarg_definition.pattern:
        schema.pattern = (
            kwarg_definition.pattern.pattern
            if isinstance(kwarg_definition.pattern, Pattern)  # type: ignore[unreachable]
            else kwarg_definition.pattern
        )
    if kwarg_definition.lower_case:
        schema.description = "must be in lower case"
    if kwarg_definition.upper_case:
        schema.description = "must be in upper case"
    return schema
