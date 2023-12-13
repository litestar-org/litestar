from __future__ import annotations

import pytest

from litestar._openapi.datastructures import SchemaRegistry
from litestar.openapi.spec import Reference, Schema


@pytest.fixture()
def schema_registry() -> SchemaRegistry:
    return SchemaRegistry()


def test_get_schema_for_key(schema_registry: SchemaRegistry) -> None:
    assert not schema_registry._schema_key_map
    assert not schema_registry._schema_reference_map
    assert not schema_registry._model_name_groups
    key = ("a", "b", "c")
    schema = schema_registry.get_schema_for_key(key)
    assert isinstance(schema, Schema)
    assert key in schema_registry._schema_key_map
    assert not schema_registry._schema_reference_map
    assert len(schema_registry._model_name_groups["c"]) == 1
    assert schema_registry._model_name_groups["c"][0].schema is schema
    assert schema_registry.get_schema_for_key(key) is schema


def test_get_reference_for_key(schema_registry: SchemaRegistry) -> None:
    assert not schema_registry._schema_key_map
    assert not schema_registry._schema_reference_map
    assert not schema_registry._model_name_groups
    key = ("a", "b", "c")
    assert schema_registry.get_reference_for_key(key) is None
    schema_registry.get_schema_for_key(key)
    reference = schema_registry.get_reference_for_key(key)
    assert isinstance(reference, Reference)
    assert id(reference) in schema_registry._schema_reference_map
    assert reference in schema_registry._schema_key_map[key].references
