from __future__ import annotations

from dataclasses import is_dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any

from _decimal import Decimal
from pydantic_factories import ModelFactory
from pydantic_factories.exceptions import ParameterError

from litestar.openapi.spec import Example
from litestar.utils import (
    convert_dataclass_to_model,
    create_parsed_model_field,
    is_pydantic_model_instance,
)

if TYPE_CHECKING:
    from litestar._signature.field import SignatureField


def normalize_example_value(value: Any) -> Any:
    """Normalize the example value to make it look a bit prettier."""
    if isinstance(value, (Decimal, float)):
        value = round(float(value), 2)
    if isinstance(value, Enum):
        value = value.value
    if is_dataclass(value):
        value = convert_dataclass_to_model(value)
    if is_pydantic_model_instance(value):
        value = value.dict()
    if isinstance(value, (list, set)):
        value = [normalize_example_value(v) for v in value]
    if isinstance(value, dict):
        for k, v in value.items():
            value[k] = normalize_example_value(v)
    return value


class ExampleFactory(ModelFactory):
    """A factory that always returns values."""

    __allow_none_optionals__ = False


def create_examples_for_field(field: "SignatureField") -> list["Example"]:
    """Use the pydantic-factories package to create an example value for the given schema."""
    try:
        model_field = create_parsed_model_field(field.field_type)
        value = normalize_example_value(ExampleFactory.get_field_value(model_field))
        return [Example(description=f"Example {field.name} value", value=value)]
    except ParameterError:  # pragma: no cover
        return []
