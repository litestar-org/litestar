from __future__ import annotations

from datetime import date, datetime, timezone
from re import Pattern
from typing import TYPE_CHECKING

from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.schema import Schema

if TYPE_CHECKING:
    from _decimal import Decimal

    from litestar.params import BodyKwarg, ParameterKwarg


__all__ = (
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
