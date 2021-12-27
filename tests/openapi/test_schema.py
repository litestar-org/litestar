from openapi_schema_pydantic import Example
from openapi_schema_pydantic.v3.v3_1_0.schema import Schema
from pydantic.fields import FieldInfo

from starlite.openapi.constants import (
    EXTRA_TO_OPENAPI_PROPERTY_MAP,
    PYDANTIC_TO_OPENAPI_PROPERTY_MAP,
)
from starlite.openapi.schema import update_schema_with_field_info


def test_update_schema_with_field_info():
    test_str = "abc"
    extra = {
        "examples": [Example(value=1)],
        "external_docs": "https://example.com/docs",
        "content_encoding": "utf-8",
    }
    field_info = FieldInfo(
        default=test_str,
        title=test_str,
        description=test_str,
        const=True,
        gt=1,
        ge=1,
        lt=1,
        le=1,
        multiple_of=1,
        min_items=1,
        max_items=1,
        min_length=1,
        max_length=1,
        regex="^[a-z]$",
        **extra,
    )
    schema = Schema()
    update_schema_with_field_info(schema=schema, field_info=field_info)
    assert schema.const == field_info.default
    for pydantic_key, schema_key in PYDANTIC_TO_OPENAPI_PROPERTY_MAP.items():
        assert getattr(schema, schema_key) == getattr(field_info, pydantic_key)
    for extra_key, schema_key in EXTRA_TO_OPENAPI_PROPERTY_MAP.items():
        assert getattr(schema, schema_key) == field_info.extra[extra_key]
