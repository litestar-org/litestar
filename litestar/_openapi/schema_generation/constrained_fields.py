from __future__ import annotations

from datetime import date, datetime, timezone
from re import Pattern
from typing import TYPE_CHECKING, Any

from _decimal import Decimal
from polyfactory.utils.predicates import is_safe_subclass

from litestar._openapi.schema_generation.utils import sort_schemas_and_references
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.schema import Schema

if TYPE_CHECKING:
    from litestar.params import BodyKwarg, ParameterKwarg
    from litestar.plugins import OpenAPISchemaPluginProtocol

if TYPE_CHECKING:
    from litestar._signature.field import SignatureField

__all__ = (
    "create_collection_constrained_field_schema",
    "create_constrained_field_schema",
    "create_date_constrained_field_schema",
    "create_numerical_constrained_field_schema",
    "create_string_constrained_field_schema",
)


def create_numerical_constrained_field_schema(
    field_type: type[int] | type[float] | type[Decimal],
    kwargs_model: ParameterKwarg | BodyKwarg,
) -> Schema:
    """Create Schema from Constrained Int/Float/Decimal field."""
    schema = Schema(type=OpenAPIType.INTEGER if issubclass(field_type, int) else OpenAPIType.NUMBER)
    if kwargs_model.le is not None:
        schema.maximum = float(kwargs_model.le)
    if kwargs_model.lt is not None:
        schema.exclusive_maximum = float(kwargs_model.lt)
    if kwargs_model.ge is not None:
        schema.minimum = float(kwargs_model.ge)
    if kwargs_model.gt is not None:
        schema.exclusive_minimum = float(kwargs_model.gt)
    if kwargs_model.multiple_of is not None:
        schema.multiple_of = float(kwargs_model.multiple_of)
    return schema


def create_date_constrained_field_schema(
    field_type: type[date] | type[datetime],
    kwargs_model: ParameterKwarg | BodyKwarg,
) -> Schema:
    """Create Schema from Constrained Date Field."""
    schema = Schema(
        type=OpenAPIType.STRING, format=OpenAPIFormat.DATE if issubclass(field_type, date) else OpenAPIFormat.DATE_TIME
    )
    for kwargs_model_attr, schema_attr in [
        ("le", "maximum"),
        ("lt", "exclusive_maximum"),
        ("ge", "minimum"),
        ("gt", "exclusive_minimum"),
    ]:
        if attr := getattr(kwargs_model, kwargs_model_attr):
            setattr(
                schema,
                schema_attr,
                datetime.combine(
                    datetime.fromtimestamp(attr, tz=timezone.utc) if isinstance(attr, (float, int)) else attr,
                    datetime.min.time(),
                    tzinfo=timezone.utc,
                ).timestamp(),
            )

    return schema


def create_string_constrained_field_schema(
    field_type: type[str] | type[bytes],
    kwargs_model: ParameterKwarg | BodyKwarg,
) -> Schema:
    """Create Schema from Constrained Str/Bytes field."""
    schema = Schema(type=OpenAPIType.STRING)
    if issubclass(field_type, bytes):
        schema.content_encoding = "utf-8"
    if kwargs_model.min_length:
        schema.min_length = kwargs_model.min_length
    if kwargs_model.max_length:
        schema.max_length = kwargs_model.max_length
    if kwargs_model.pattern:
        schema.pattern = (
            kwargs_model.pattern.pattern if isinstance(kwargs_model.pattern, Pattern) else kwargs_model.pattern  # type: ignore[attr-defined,unreachable]
        )
    if kwargs_model.lower_case:
        schema.description = "must be in lower case"
    if kwargs_model.upper_case:
        schema.description = "must be in upper case"
    return schema


def create_collection_constrained_field_schema(
    children: tuple[SignatureField, ...] | None,
    field_type: type[list] | type[set] | type[frozenset] | type[tuple],
    kwargs_model: ParameterKwarg | BodyKwarg,
    plugins: list[OpenAPISchemaPluginProtocol],
    schemas: dict[str, Schema],
    prefer_alias: bool,
) -> Schema:
    """Create Schema from Constrained List/Set field.

    Args:
        children: Any child fields.
        field_type: A constrained field type.
        kwargs_model:  A constrained field model.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.
        prefer_alias: Whether to prefer the alias name for the schema.

    Returns:
        A schema instance.
    """

    from litestar._openapi.schema_generation import create_schema

    schema = Schema(type=OpenAPIType.ARRAY)
    if kwargs_model.min_items:
        schema.min_items = kwargs_model.min_items
    if kwargs_model.max_items:
        schema.max_items = kwargs_model.max_items
    if any(is_safe_subclass(field_type, t) for t in (set, frozenset)):  # type: ignore[arg-type]
        schema.unique_items = True
    if children:
        items = [
            create_schema(
                field=sub_field, generate_examples=False, plugins=plugins, schemas=schemas, prefer_alias=prefer_alias
            )
            for sub_field in children
        ]
        if len(items) > 1:
            schema.items = Schema(one_of=sort_schemas_and_references(items))
        else:
            schema.items = items[0]
    else:
        from litestar._signature.field import SignatureField

        schema.items = create_schema(
            field=SignatureField.create(field_type=field_type.item_type, name=f"{field_type.__name__}Field"),  # type: ignore[union-attr]
            generate_examples=False,
            plugins=plugins,
            schemas=schemas,
            prefer_alias=prefer_alias,
        )
    return schema


def create_constrained_field_schema(
    children: tuple[SignatureField, ...] | None,
    field_type: Any,
    kwargs_model: ParameterKwarg | BodyKwarg,
    plugins: list[OpenAPISchemaPluginProtocol],
    schemas: dict[str, Schema],
    prefer_alias: bool,
) -> Schema:
    """Create Schema for Pydantic Constrained fields (created using constr(), conint() and so forth, or by subclassing
    Constrained*)

    Args:
        children: Any children.
        field_type: A constrained field type.
        kwargs_model:  A constrained field model.
        plugins: A list of plugins.
        schemas: A mapping of namespaces to schemas - this mapping is used in the OA components section.
        prefer_alias: Whether to prefer the alias name for the schema.

    Returns:
        A schema instance.

    """
    if any(is_safe_subclass(field_type, t) for t in (int, float, Decimal)):
        return create_numerical_constrained_field_schema(field_type=field_type, kwargs_model=kwargs_model)
    if any(is_safe_subclass(field_type, t) for t in (str, bytes)):  # type: ignore[arg-type]
        return create_string_constrained_field_schema(field_type=field_type, kwargs_model=kwargs_model)
    if any(is_safe_subclass(field_type, t) for t in (date, datetime)):
        return create_date_constrained_field_schema(field_type=field_type, kwargs_model=kwargs_model)
    return create_collection_constrained_field_schema(
        field_type=field_type,
        children=tuple(children) if children else None,
        plugins=plugins,
        schemas=schemas,
        prefer_alias=prefer_alias,
        kwargs_model=kwargs_model,
    )
