from datetime import date
from typing import Any, Pattern, Union

import pytest
from pydantic import conlist, conset

from litestar._openapi.schema_generation.constrained_fields import (
    create_date_constrained_field_schema,
    create_numerical_constrained_field_schema,
    create_string_constrained_field_schema,
)
from litestar._openapi.schema_generation.schema import SchemaCreator
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.params import KwargDefinition
from litestar.typing import FieldDefinition

from .utils import (
    constrained_collection,
    constrained_dates,
    constrained_numbers,
    constrained_string,
)


@pytest.mark.parametrize("annotation", constrained_collection)
def test_create_collection_constrained_field_schema(annotation: Any) -> None:
    schema = SchemaCreator().for_collection_constrained_field(FieldDefinition.from_annotation(annotation))
    assert schema.type == OpenAPIType.ARRAY
    assert schema.items.type == OpenAPIType.INTEGER  # type: ignore[union-attr]
    assert schema.min_items == annotation.min_items
    assert schema.max_items == annotation.max_items


def test_create_collection_constrained_field_schema_sub_fields() -> None:
    for pydantic_fn in (conlist, conset):
        field_definition = FieldDefinition.from_annotation(pydantic_fn(Union[str, int], min_items=1, max_items=10))  # type: ignore
        schema = SchemaCreator().for_collection_constrained_field(field_definition)
        assert schema.type == OpenAPIType.ARRAY
        expected = {
            "items": {"oneOf": [{"type": "integer"}, {"type": "string"}]},
            "maxItems": 10,
            "minItems": 1,
            "type": "array",
        }
        if pydantic_fn == conset:
            # set should have uniqueItems always
            expected["uniqueItems"] = True

        assert schema.to_schema() == expected


@pytest.mark.parametrize("annotation", constrained_string)
def test_create_string_constrained_field_schema(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)

    assert isinstance(field_definition.kwarg_definition, KwargDefinition)
    schema = create_string_constrained_field_schema(field_definition.annotation, field_definition.kwarg_definition)
    assert schema.type == OpenAPIType.STRING
    assert schema.min_length == annotation.min_length
    assert schema.max_length == annotation.max_length
    if pattern := getattr(annotation, "regex", getattr(annotation, "pattern", None)):
        assert schema.pattern == pattern.pattern if isinstance(pattern, Pattern) else pattern
    if annotation.to_lower:
        assert schema.description
    if annotation.to_upper:
        assert schema.description


@pytest.mark.parametrize("annotation", constrained_numbers)
def test_create_numerical_constrained_field_schema(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)

    assert isinstance(field_definition.kwarg_definition, KwargDefinition)
    schema = create_numerical_constrained_field_schema(field_definition.annotation, field_definition.kwarg_definition)
    assert schema.type == OpenAPIType.INTEGER if issubclass(annotation, int) else OpenAPIType.NUMBER
    assert schema.exclusive_minimum == annotation.gt
    assert schema.minimum == annotation.ge
    assert schema.exclusive_maximum == annotation.lt
    assert schema.maximum == annotation.le
    assert schema.multiple_of == annotation.multiple_of


@pytest.mark.parametrize("annotation", constrained_dates)
def test_create_date_constrained_field_schema(annotation: Any) -> None:
    field_definition = FieldDefinition.from_annotation(annotation)

    assert isinstance(field_definition.kwarg_definition, KwargDefinition)
    schema = create_date_constrained_field_schema(field_definition.annotation, field_definition.kwarg_definition)
    assert schema.type == OpenAPIType.STRING
    assert schema.format == OpenAPIFormat.DATE
    assert (date.fromtimestamp(schema.exclusive_minimum) if schema.exclusive_minimum else None) == annotation.gt
    assert (date.fromtimestamp(schema.minimum) if schema.minimum else None) == annotation.ge
    assert (date.fromtimestamp(schema.exclusive_maximum) if schema.exclusive_maximum else None) == annotation.lt
    assert (date.fromtimestamp(schema.maximum) if schema.maximum else None) == annotation.le


@pytest.mark.parametrize(
    "annotation", [*constrained_numbers, *constrained_collection, *constrained_string, *constrained_dates]
)
def test_create_constrained_field_schema(annotation: Any) -> None:
    schema = SchemaCreator().for_constrained_field(FieldDefinition.from_annotation(annotation))
    assert schema
