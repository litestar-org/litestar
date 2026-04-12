"""Tests for OpenAPI schema generation of nullable required fields.

Verifies that fields typed as ``T | None`` (nullable) without a default are correctly
included in the ``required`` array of the generated OpenAPI schema. This addresses
GitHub issue #4673 where Litestar conflated "nullable" with "optional".
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import attrs
import msgspec
import pytest
from pydantic import BaseModel

from litestar import get, post
from litestar.openapi.spec import Reference
from litestar.testing import create_test_client
from litestar.typing import FieldDefinition
from tests.helpers import get_schema_for_field_definition

# ─── Model Definitions ───────────────────────────────────────────────


@dataclass
class DataclassModel:
    required_non_nullable: int
    required_nullable: int | None
    optional_nullable: int | None = None
    optional_non_nullable: int = 0


class MsgspecModel(msgspec.Struct):
    required_non_nullable: int
    required_nullable: int | None
    optional_nullable: int | None = None
    optional_non_nullable: int = 0


@attrs.define
class AttrsModel:
    required_non_nullable: int
    required_nullable: int | None
    optional_nullable: int | None = None
    optional_non_nullable: int = 0


class PydanticModel(BaseModel):
    required_non_nullable: int
    required_nullable: int | None
    optional_nullable: int | None = None
    optional_non_nullable: int = 0


# ─── Schema Tests ────────────────────────────────────────────────────

EXPECTED_REQUIRED = sorted(["required_non_nullable", "required_nullable"])


@pytest.mark.parametrize(
    "model",
    [
        pytest.param(DataclassModel, id="dataclass"),
        pytest.param(MsgspecModel, id="msgspec"),
    ],
)
def test_nullable_required_fields_in_schema_direct(model: type) -> None:
    """Fields typed ``T | None`` without a default must appear in ``required`` (schema-level test)."""
    schema = get_schema_for_field_definition(FieldDefinition.from_kwarg(name="Model", annotation=model))

    assert schema.required is not None, f"Schema for {model.__name__} has no required fields"
    assert sorted(schema.required) == EXPECTED_REQUIRED, (
        f"Schema for {model.__name__}: expected required={EXPECTED_REQUIRED}, got {sorted(schema.required)}"
    )


@pytest.mark.parametrize(
    "model",
    [
        pytest.param(DataclassModel, id="dataclass"),
        pytest.param(MsgspecModel, id="msgspec"),
    ],
)
def test_optional_nullable_fields_not_required_direct(model: type) -> None:
    """Fields typed ``T | None = None`` (with default) must NOT appear in ``required`` (schema-level test)."""
    schema = get_schema_for_field_definition(FieldDefinition.from_kwarg(name="Model", annotation=model))

    required = schema.required or []
    assert "optional_nullable" not in required
    assert "optional_non_nullable" not in required


def _assert_handler_schema_required(client_cm: Any, model_name: str) -> None:
    """Helper to assert required fields in a handler's response schema."""
    with client_cm as client:
        openapi = client.app.openapi_schema.to_schema()
        components = openapi.get("components", {}).get("schemas", {})
        model_schema = next(
            (s for name, s in components.items() if model_name in name),
            None,
        )
        assert model_schema is not None, f"{model_name} not found in components: {list(components.keys())}"
        required = sorted(model_schema.get("required", []))
        assert required == EXPECTED_REQUIRED, f"{model_name}: expected required={EXPECTED_REQUIRED}, got {required}"


def test_nullable_required_fields_in_handler_dataclass() -> None:
    """Dataclass: nullable required fields in handler return type appear in required array."""

    @post("/test")
    def handler(data: DataclassModel) -> DataclassModel:
        return data

    _assert_handler_schema_required(create_test_client(handler), "DataclassModel")


def test_nullable_required_fields_in_handler_msgspec() -> None:
    """Msgspec: nullable required fields in handler return type appear in required array."""

    @post("/test")
    def handler(data: MsgspecModel) -> MsgspecModel:
        return data

    _assert_handler_schema_required(create_test_client(handler), "MsgspecModel")


def test_nullable_required_fields_in_handler_attrs() -> None:
    """Attrs: nullable required fields in handler return type appear in required array."""

    @post("/test")
    def handler(data: AttrsModel) -> AttrsModel:
        return data

    _assert_handler_schema_required(create_test_client(handler), "AttrsModel")


def test_nullable_required_fields_in_handler_pydantic() -> None:
    """Pydantic: nullable required fields in handler return type appear in required array."""

    @post("/test")
    def handler(data: PydanticModel) -> PydanticModel:
        return data

    _assert_handler_schema_required(create_test_client(handler), "PydanticModel")


# ─── FieldDefinition.is_required Tests ───────────────────────────────


def test_field_definition_is_required_nullable_no_default() -> None:
    """A nullable field without a default must be required."""
    field = FieldDefinition.from_annotation(int | None, name="test")
    assert field.is_required is True


def test_field_definition_is_required_nullable_with_default() -> None:
    """A nullable field with a default must NOT be required."""
    field = FieldDefinition.from_kwarg(annotation=int | None, name="test", default=None)
    assert field.is_required is False


def test_field_definition_is_required_non_nullable_no_default() -> None:
    """A non-nullable field without a default must be required."""
    field = FieldDefinition.from_annotation(int, name="test")
    assert field.is_required is True


def test_field_definition_is_required_non_nullable_with_default() -> None:
    """A non-nullable field with a default must NOT be required."""
    field = FieldDefinition.from_kwarg(annotation=int, name="test", default=0)
    assert field.is_required is False


# ─── Integration: OpenAPI Parameter Tests ────────────────────────────


def test_nullable_query_param_required_in_openapi_schema() -> None:
    """A query parameter typed ``int | None`` without a default must be required in the OpenAPI schema."""

    @get("/test")
    def handler(required_nullable_param: int | None) -> dict:
        return {}

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema.paths
        path_item = schema.paths["/test"]
        assert path_item and path_item.get
        params = {p.name: p for p in (path_item.get.parameters or [])}  # type: ignore[union-attr]
        assert "required_nullable_param" in params
        param = params["required_nullable_param"]
        assert not isinstance(param, Reference)
        assert param.required is True


def test_nullable_query_param_optional_with_default_in_openapi_schema() -> None:
    """A query parameter typed ``int | None = None`` must NOT be required in the OpenAPI schema."""

    @get("/test")
    def handler(optional_nullable_param: int | None = None) -> dict:
        return {}

    with create_test_client(handler) as client:
        schema = client.app.openapi_schema
        assert schema.paths
        path_item = schema.paths["/test"]
        assert path_item and path_item.get
        params = {p.name: p for p in (path_item.get.parameters or [])}  # type: ignore[union-attr]
        assert "optional_nullable_param" in params
        param = params["optional_nullable_param"]
        assert not isinstance(param, Reference)
        assert param.required is False


# ─── Integration: Full Handler Return Type Tests ─────────────────────


def test_nullable_required_in_handler_return_type() -> None:
    """Nullable required fields in a handler's return type must appear in the response schema's required array."""

    @get("/test")
    def handler() -> PydanticModel:
        return PydanticModel(required_non_nullable=1, required_nullable=None)

    with create_test_client(handler) as client:
        openapi = client.app.openapi_schema.to_schema()
        components = openapi.get("components", {}).get("schemas", {})
        # Find the PydanticModel schema
        model_schema = None
        for name, schema in components.items():
            if "PydanticModel" in name:
                model_schema = schema
                break
        assert model_schema is not None, f"PydanticModel not found in components: {list(components.keys())}"
        assert sorted(model_schema.get("required", [])) == EXPECTED_REQUIRED
