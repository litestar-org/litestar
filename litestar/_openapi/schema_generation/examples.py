from __future__ import annotations

from dataclasses import replace
from enum import Enum
from typing import TYPE_CHECKING, Any

from _decimal import Decimal
from polyfactory.exceptions import ParameterException
from polyfactory.field_meta import FieldMeta, Null
from polyfactory.utils.helpers import unwrap_annotation

from litestar.openapi.spec import Example
from litestar.types import Empty
from litestar.utils import is_pydantic_model_instance

try:
    from polyfactory.factories.pydantic_factory import ModelFactory as Factory
except ImportError:
    from polyfactory.factories import DataclassFactory as Factory  # type: ignore[assignment]


if TYPE_CHECKING:
    from litestar.typing import FieldDefinition


Factory.seed_random(10)


def _normalize_example_value(value: Any) -> Any:
    """Normalize the example value to make it look a bit prettier."""
    value = unwrap_annotation(annotation=value, random=Factory.__random__)
    if isinstance(value, (Decimal, float)):
        value = round(float(value), 2)
    if isinstance(value, Enum):
        value = value.value
    if is_pydantic_model_instance(value):
        from litestar.contrib.pydantic import _model_dump

        value = _model_dump(value)
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
        random=Factory.__random__,
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
        value = Factory.get_field_value(field_meta)
        return [Example(description=f"Example {field.name} value", value=value)]
    except ParameterException:
        return []
