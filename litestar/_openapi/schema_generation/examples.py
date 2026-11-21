from __future__ import annotations

import typing
from dataclasses import replace
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING, Any, get_args
from uuid import UUID

import msgspec
from polyfactory.exceptions import ParameterException
from polyfactory.factories import DataclassFactory
from polyfactory.field_meta import FieldMeta, Null
from polyfactory.utils.helpers import unwrap_annotation
from polyfactory.utils.predicates import is_union

from litestar.openapi.spec import Example
from litestar.types import Empty

if TYPE_CHECKING:
    from collections.abc import Callable

    from litestar.typing import FieldDefinition


class ExampleFactory(DataclassFactory[Example]):
    __model__ = Example
    __random_seed__ = 10
    __check_model__ = False


def _normalize_example_value(value: Any) -> Any:
    """Normalize the example value to make it look a bit prettier."""
    # if UnsetType is part of the union, then it might get chosen as the value
    # but that will not be properly serialized by msgspec unless it is for a field
    # in a msgspec Struct
    if is_union(value):
        args = list(get_args(value))
        try:
            args.remove(msgspec.UnsetType)
            value = typing.Union[tuple(args)]
        except ValueError:
            # UnsetType not part of the Union
            pass

    value = unwrap_annotation(annotation=value)
    if isinstance(value, (Decimal, float)):
        value = round(float(value), 2)
    if isinstance(value, Enum):
        value = value.value
    if isinstance(value, (list, set)):
        value = [_normalize_example_value(v) for v in value]
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = _normalize_example_value(v)
    return value


def _create_field_meta(field: FieldDefinition) -> FieldMeta:
    return FieldMeta.from_type(
        annotation=field.annotation,
        default=field.default if field.default is not Empty else Null,
        name=field.name,
    )


def create_examples_for_field(field: FieldDefinition) -> list[Example]:
    """Create an OpenAPI Example instance.

    Args:
        field: A signature field.

    Returns:
        A list including a single example.
    """
    try:
        field_meta = _create_field_meta(replace(field, annotation=_normalize_example_value(field.annotation)))
        value = ExampleFactory.get_field_value(field_meta)
        return [Example(description=f"Example {field.name} value", value=value)]
    except (ParameterException, ValueError):
        return []


def create_input_examples(examples: list[Example], input_value: Callable[[Any], Any]) -> list[Example]:
    """Convert generated examples to values the server accepts as input, or drop them if it would not.

    Args:
        examples: Examples created by :func:`create_examples_for_field`.
        input_value: Converts any value msgspec cannot convert to a value validation accepts, or raises
            ``TypeError``.

    Returns:
        The converted examples, or an empty list.
    """
    try:
        return [
            replace(
                example,
                value=msgspec.to_builtins(
                    example.value,
                    builtin_types=(datetime, date, time, Decimal, UUID, bytes),
                    enc_hook=input_value,
                ),
            )
            for example in examples
        ]
    except (TypeError, ValueError):
        return []
