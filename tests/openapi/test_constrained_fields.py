from typing import Any, List, Union

from hypothesis import given
from hypothesis import strategies as st
from pydantic import conlist, conset

from starlite.openapi.enums import OpenAPIType
from starlite.openapi.schema import (
    create_collection_constrained_field_schema,
    create_constrained_field_schema,
    create_numerical_constrained_field_schema,
    create_string_constrained_field_schema,
)
from starlite.utils.model import create_parsed_model_field
from tests.openapi.utils import (
    constrained_collection,
    constrained_numbers,
    constrained_string,
)


@given(
    field_type=st.sampled_from(constrained_collection),
)
def test_create_collection_constrained_field_schema(field_type: Any) -> None:
    schema = create_collection_constrained_field_schema(field_type=field_type, sub_fields=None)
    assert schema.type == OpenAPIType.ARRAY
    assert schema.items.type == OpenAPIType.INTEGER
    assert schema.minItems == field_type.min_items
    assert schema.maxItems == field_type.max_items


def test_create_collection_constrained_field_schema_sub_fields() -> None:
    field_type = List[Union[str, int]]
    for pydantic_fn in [conlist, conset]:
        schema = create_collection_constrained_field_schema(
            field_type=pydantic_fn(field_type, min_items=1, max_items=10),  # type: ignore
            sub_fields=create_parsed_model_field(field_type).sub_fields,
        )
        assert schema.type == OpenAPIType.ARRAY
        expected = {
            "items": [{"oneOf": [{"type": "string"}, {"type": "integer"}]}],
            "type": "array",
            "maxItems": 10,
            "minItems": 1,
        }
        if pydantic_fn == conset:
            # set should have uniqueItems always
            expected["uniqueItems"] = True

        assert schema.dict(exclude_none=True) == expected


@given(field_type=st.sampled_from(constrained_string))
def test_create_string_constrained_field_schema(field_type: Any) -> None:
    schema = create_string_constrained_field_schema(field_type=field_type)
    assert schema.type == OpenAPIType.STRING
    assert schema.minLength == field_type.min_length
    assert schema.maxLength == field_type.max_length
    if hasattr(field_type, "regex"):
        assert schema.pattern == field_type.regex
    if field_type.to_lower:
        assert schema.description


@given(field_type=st.sampled_from(constrained_numbers))
def test_create_numerical_constrained_field_schema(field_type: Any) -> None:
    schema = create_numerical_constrained_field_schema(field_type=field_type)
    assert schema.type == OpenAPIType.INTEGER if issubclass(field_type, int) else OpenAPIType.NUMBER
    assert schema.exclusiveMinimum == field_type.gt
    assert schema.minimum == field_type.ge
    assert schema.exclusiveMaximum == field_type.lt
    assert schema.maximum == field_type.le
    assert schema.exclusiveMinimum == field_type.gt
    assert schema.multipleOf == field_type.multiple_of


@given(field_type=st.sampled_from([*constrained_numbers, *constrained_collection, *constrained_string]))
def test_create_constrained_field_schema(field_type: Any) -> None:
    schema = create_constrained_field_schema(field_type=field_type, sub_fields=None)
    assert schema
