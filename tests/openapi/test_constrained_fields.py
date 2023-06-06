from datetime import date
from typing import Any, Pattern, Union

import pytest
from pydantic import conlist, conset

from litestar._openapi.schema_generation.constrained_fields import (
    create_collection_constrained_field_schema,
    create_constrained_field_schema,
    create_date_constrained_field_schema,
    create_numerical_constrained_field_schema,
    create_string_constrained_field_schema,
)
from litestar._signature.field import SignatureField
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from tests.openapi.utils import (
    constrained_collection,
    constrained_dates,
    constrained_numbers,
    constrained_string,
)


@pytest.mark.parametrize("field_type", constrained_collection)
def test_create_collection_constrained_field_schema(field_type: Any) -> None:
    signature_field = SignatureField.create(field_type=field_type)
    schema = create_collection_constrained_field_schema(
        field_type=signature_field.field_type,
        children=signature_field.children,
        kwargs_model=signature_field.kwarg_model,  # type: ignore[arg-type]
        plugins=[],
        schemas={},
    )
    assert schema.type == OpenAPIType.ARRAY
    assert schema.items.type == OpenAPIType.INTEGER  # type: ignore
    assert schema.min_items == field_type.min_items
    assert schema.max_items == field_type.max_items


def test_create_collection_constrained_field_schema_sub_fields() -> None:
    for pydantic_fn in (conlist, conset):
        signature_field = SignatureField.create(field_type=pydantic_fn(Union[str, int], min_items=1, max_items=10))  # type: ignore
        schema = create_collection_constrained_field_schema(
            field_type=signature_field.field_type,
            children=signature_field.children,
            kwargs_model=signature_field.kwarg_model,  # type: ignore[arg-type]
            plugins=[],
            schemas={},
        )
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


@pytest.mark.parametrize("field_type", constrained_string)
def test_create_string_constrained_field_schema(field_type: Any) -> None:
    signature_field = SignatureField.create(field_type=field_type)
    schema = create_string_constrained_field_schema(
        field_type=signature_field.field_type, kwargs_model=signature_field.kwarg_model  # type: ignore[arg-type]
    )
    assert schema.type == OpenAPIType.STRING
    assert schema.min_length == field_type.min_length
    assert schema.max_length == field_type.max_length
    if pattern := getattr(field_type, "regex", getattr(field_type, "pattern", None)):
        assert schema.pattern == pattern.pattern if isinstance(pattern, Pattern) else pattern
    if field_type.to_lower:
        assert schema.description
    if field_type.to_upper:
        assert schema.description


@pytest.mark.parametrize("field_type", constrained_numbers)
def test_create_numerical_constrained_field_schema(field_type: Any) -> None:
    signature_field = SignatureField.create(field_type=field_type)
    schema = create_numerical_constrained_field_schema(
        field_type=signature_field.field_type, kwargs_model=signature_field.kwarg_model  # type: ignore[arg-type]
    )
    assert schema.type == OpenAPIType.INTEGER if issubclass(field_type, int) else OpenAPIType.NUMBER
    assert schema.exclusive_minimum == field_type.gt
    assert schema.minimum == field_type.ge
    assert schema.exclusive_maximum == field_type.lt
    assert schema.maximum == field_type.le
    assert schema.multiple_of == field_type.multiple_of


@pytest.mark.parametrize("field_type", constrained_dates)
def test_create_date_constrained_field_schema(field_type: Any) -> None:
    signature_field = SignatureField.create(field_type=field_type)
    schema = create_date_constrained_field_schema(
        field_type=signature_field.field_type, kwargs_model=signature_field.kwarg_model  # type: ignore[arg-type]
    )
    assert schema.type == OpenAPIType.STRING
    assert schema.format == OpenAPIFormat.DATE
    assert (date.fromtimestamp(schema.exclusive_minimum) if schema.exclusive_minimum else None) == field_type.gt
    assert (date.fromtimestamp(schema.minimum) if schema.minimum else None) == field_type.ge
    assert (date.fromtimestamp(schema.exclusive_maximum) if schema.exclusive_maximum else None) == field_type.lt
    assert (date.fromtimestamp(schema.maximum) if schema.maximum else None) == field_type.le


@pytest.mark.parametrize(
    "field_type", [*constrained_numbers, *constrained_collection, *constrained_string, *constrained_dates]
)
def test_create_constrained_field_schema(field_type: Any) -> None:
    signature_field = SignatureField.create(field_type=field_type)
    schema = create_constrained_field_schema(
        field_type=field_type,
        children=signature_field.children,
        kwargs_model=signature_field.kwarg_model,  # type: ignore[arg-type]
        plugins=[],
        schemas={},
    )
    assert schema
