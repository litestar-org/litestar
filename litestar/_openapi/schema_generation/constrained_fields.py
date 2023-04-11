from __future__ import annotations

from datetime import datetime
from re import Pattern
from typing import TYPE_CHECKING, Any

from litestar._openapi.schema_generation.utils import sort_schemas_and_references
from litestar.exceptions import MissingDependencyException
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.schema import Schema

if TYPE_CHECKING:
    from litestar.plugins import OpenAPISchemaPluginProtocol

if TYPE_CHECKING:
    from litestar._signature.field import SignatureField

    try:
        from pydantic import (
            ConstrainedBytes,
            ConstrainedDate,
            ConstrainedDecimal,
            ConstrainedFloat,
            ConstrainedFrozenSet,
            ConstrainedInt,
            ConstrainedList,
            ConstrainedSet,
            ConstrainedStr,
        )
    except ImportError:
        ConstrainedBytes = Any  # type: ignore
        ConstrainedDate = Any  # type: ignore
        ConstrainedDecimal = Any  # type: ignore
        ConstrainedFloat = Any  # type: ignore
        ConstrainedFrozenSet = Any  # type: ignore
        ConstrainedInt = Any  # type: ignore
        ConstrainedList = Any  # type: ignore
        ConstrainedSet = Any  # type: ignore
        ConstrainedStr = Any  # type: ignore


__all__ = (
    "create_collection_constrained_field_schema",
    "create_constrained_field_schema",
    "create_date_constrained_field_schema",
    "create_numerical_constrained_field_schema",
    "create_string_constrained_field_schema",
)


def create_numerical_constrained_field_schema(
    field_type: type["ConstrainedFloat"] | type["ConstrainedInt"] | type["ConstrainedDecimal"],
) -> Schema:
    """Create Schema from Constrained Int/Float/Decimal field."""
    schema = Schema(type=OpenAPIType.INTEGER if issubclass(field_type, int) else OpenAPIType.NUMBER)
    if field_type.le is not None:
        schema.maximum = float(field_type.le)
    if field_type.lt is not None:
        schema.exclusive_maximum = float(field_type.lt)
    if field_type.ge is not None:
        schema.minimum = float(field_type.ge)
    if field_type.gt is not None:
        schema.exclusive_minimum = float(field_type.gt)
    if field_type.multiple_of is not None:
        schema.multiple_of = float(field_type.multiple_of)
    return schema


def create_date_constrained_field_schema(field_type: type["ConstrainedDate"]) -> Schema:
    """Create Schema from Constrained Date Field."""
    schema = Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE)
    if field_type.le is not None:
        schema.maximum = float(datetime.combine(field_type.le, datetime.min.time()).timestamp())
    if field_type.lt is not None:
        schema.exclusive_maximum = float(datetime.combine(field_type.lt, datetime.min.time()).timestamp())
    if field_type.ge is not None:
        schema.minimum = float(datetime.combine(field_type.ge, datetime.min.time()).timestamp())
    if field_type.gt is not None:
        schema.exclusive_minimum = float(datetime.combine(field_type.gt, datetime.min.time()).timestamp())
    return schema


def create_string_constrained_field_schema(field_type: type["ConstrainedStr"] | type["ConstrainedBytes"]) -> Schema:
    """Create Schema from Constrained Str/Bytes field."""
    schema = Schema(type=OpenAPIType.STRING)
    if field_type.min_length:
        schema.min_length = field_type.min_length
    if field_type.max_length:
        schema.max_length = field_type.max_length
    if hasattr(field_type, "regex") and isinstance(field_type.regex, Pattern):
        schema.pattern = field_type.regex.pattern
    if field_type.to_lower:
        schema.description = "must be in lower case"
    return schema


def create_collection_constrained_field_schema(
    field_type: type["ConstrainedList"] | type["ConstrainedSet"] | type["ConstrainedFrozenSet"],
    children: tuple["SignatureField", ...] | None,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> Schema:
    """Create Schema from Constrained List/Set field.

    Args:
        field_type: A constrained field type.
        children: Any child fields.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.
    """
    import pydantic

    from litestar._openapi.schema_generation import create_schema

    schema = Schema(type=OpenAPIType.ARRAY)
    if field_type.min_items:
        schema.min_items = field_type.min_items
    if field_type.max_items:
        schema.max_items = field_type.max_items
    if issubclass(field_type, (pydantic.ConstrainedSet, pydantic.ConstrainedFrozenSet)):
        schema.unique_items = True
    if children:
        items = [
            create_schema(field=sub_field, generate_examples=False, plugins=plugins, schemas=schemas)
            for sub_field in children
        ]
        if len(items) > 1:
            schema.items = Schema(one_of=sort_schemas_and_references(items))
        else:
            schema.items = items[0]
    else:
        from litestar._signature.field import SignatureField

        schema.items = create_schema(
            field=SignatureField.create(field_type=field_type.item_type, name=f"{field_type.__name__}Field"),
            generate_examples=False,
            plugins=plugins,
            schemas=schemas,
        )
    return schema


def create_constrained_field_schema(
    field_type: type["ConstrainedBytes"]
    | type["ConstrainedDate"]
    | type["ConstrainedDecimal"]
    | type["ConstrainedFloat"]
    | type["ConstrainedFrozenSet"]
    | type["ConstrainedInt"]
    | type["ConstrainedList"]
    | type["ConstrainedSet"]
    | type["ConstrainedStr"],
    children: tuple["SignatureField", ...] | None,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, Schema],
) -> "Schema":
    """Create Schema for Pydantic Constrained fields (created using constr(), conint() and so forth, or by subclassing
    Constrained*)

    Args:
        field_type: A constrained field type.
        children: Any children.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.

    Returns:
        A schema instance.

    """

    try:
        import pydantic
    except ImportError as e:
        raise MissingDependencyException("pydantic") from e

    if issubclass(field_type, (pydantic.ConstrainedFloat, pydantic.ConstrainedInt, pydantic.ConstrainedDecimal)):
        return create_numerical_constrained_field_schema(field_type=field_type)
    if issubclass(field_type, (pydantic.ConstrainedStr, pydantic.ConstrainedBytes)):
        return create_string_constrained_field_schema(field_type=field_type)
    if issubclass(field_type, pydantic.ConstrainedDate):
        return create_date_constrained_field_schema(field_type=field_type)
    return create_collection_constrained_field_schema(
        field_type=field_type, children=tuple(children) if children else None, plugins=plugins, schemas=schemas
    )
