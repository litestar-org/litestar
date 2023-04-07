from __future__ import annotations

from enum import Enum
from typing import TYPE_CHECKING, Any

from _decimal import Decimal
from polyfactory.exceptions import ParameterException
from polyfactory.field_meta import FieldMeta, Null

from litestar.openapi.spec import Example
from litestar.types import Empty
from litestar.utils import is_pydantic_model_instance

try:
    from polyfactory.factories.pydantic_factory import ModelFactory as Factory
except ImportError:
    from polyfactory.factories import DataclassFactory as Factory  # type: ignore[assignment]


if TYPE_CHECKING:
    from litestar._signature.field import SignatureField


def _normalize_example_value(value: Any) -> Any:
    """Normalize the example value to make it look a bit prettier."""
    if isinstance(value, (Decimal, float)):
        value = round(float(value), 2)
    if isinstance(value, Enum):
        value = value.value
    if is_pydantic_model_instance(value):
        value = value.dict()
    if isinstance(value, (list, set)):
        value = [_normalize_example_value(v) for v in value]
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = _normalize_example_value(v)
    return value


def _create_field_meta(field: "SignatureField") -> FieldMeta:
    return FieldMeta(
        name=field.name,
        annotation=field.field_type,
        constant=field.is_const,
        default=field.default_value if field.default_value is not Empty else Null,
        children=[_create_field_meta(child) for child in field.children] if field.children else None,
    )


def create_examples_for_field(field: "SignatureField") -> list["Example"]:
    """Create an OpenAPI Example instance.

    Args:
        field: A signature field.

    Returns:
        A list including a single example.
    """
    try:
        field_meta = _create_field_meta(field)
        value = _normalize_example_value(Factory.get_field_value(field_meta))
        return [Example(description=f"Example {field.name} value", value=value)]
    except ParameterException:  # pragma: no cover
        return []
