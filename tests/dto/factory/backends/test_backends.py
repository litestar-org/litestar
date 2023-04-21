# ruff: noqa: UP006
from __future__ import annotations

import sys
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

import pytest
from msgspec import Struct, field, to_builtins
from pydantic import BaseModel, Field

from litestar.dto.factory.backends import MsgspecDTOBackend, PydanticDTOBackend
from litestar.dto.factory.backends.abc import BackendContext
from litestar.dto.factory.types import FieldDefinition, NestedFieldDefinition
from litestar.enums import MediaType
from litestar.exceptions import SerializationException
from litestar.openapi.spec.reference import Reference
from litestar.types.empty import Empty
from litestar.utils.signature import ParsedType

if TYPE_CHECKING:
    from typing import Any

    from litestar.dto.factory.backends import AbstractDTOBackend
    from litestar.dto.factory.types import FieldDefinitionsType


DESTRUCTURED = {
    "a": 1,
    "b": "b",
    "c": [],
    "nested": {"a": 1, "b": "two"},
}


@dataclass
class NestedDC:
    a: int
    b: str


@dataclass
class DC:
    a: int
    b: str
    c: List[int]
    nested: NestedDC


class NestedModel(BaseModel):
    a: int
    b: str


class MyModel(BaseModel):
    a: int
    b: str = "b"
    c: List[int] = Field(default_factory=list)
    nested: NestedModel


class NestedStruct(Struct):
    a: int
    b: str


class MyStruct(Struct):
    a: int
    nested: NestedStruct
    b: str = "b"
    c: List[int] = field(default_factory=list)


@pytest.fixture(name="field_definitions")
def fx_field_definitions() -> FieldDefinitionsType:
    return {
        "a": FieldDefinition(name="a", parsed_type=ParsedType(int), default=Empty),
        "b": FieldDefinition(name="b", parsed_type=ParsedType(str), default="b"),
        "c": FieldDefinition(name="c", parsed_type=ParsedType(List[int]), default_factory=list, default=Empty),
        "nested": NestedFieldDefinition(
            field_definition=FieldDefinition(name="nested", parsed_type=ParsedType(NestedDC), default=Empty),
            nested_type=NestedDC,
            nested_field_definitions={
                "a": FieldDefinition(name="a", parsed_type=ParsedType(int), default=Empty),
                "b": FieldDefinition(name="b", parsed_type=ParsedType(str), default=Empty),
            },
        ),
    }


@pytest.fixture(name="backend", params=[MsgspecDTOBackend, PydanticDTOBackend])
def fx_backend(request: Any, field_definitions: FieldDefinitionsType) -> AbstractDTOBackend:
    ctx = BackendContext(ParsedType(DC), field_definitions)
    return request.param(ctx)  # type:ignore[no-any-return]


def _destructure(model: BaseModel | Struct) -> dict[str, Any]:
    if isinstance(model, BaseModel):
        return model.dict()
    return to_builtins(model)  # type:ignore[no-any-return]


def test_backend_parse_raw_json(backend: AbstractDTOBackend) -> None:
    assert (
        _destructure(backend.parse_raw(b'{"a":1,"nested":{"a":1,"b":"two"}}', media_type=MediaType.JSON))
        == DESTRUCTURED
    )


def test_backend_parse_raw_msgpack(backend: AbstractDTOBackend) -> None:
    assert (
        _destructure(
            backend.parse_raw(b"\x82\xa1a\x01\xa6nested\x82\xa1a\x01\xa1b\xa3two", media_type=MediaType.MESSAGEPACK)
        )
        == DESTRUCTURED
    )


def test_backend_parse_unsupported_media_type(backend: AbstractDTOBackend) -> None:
    with pytest.raises(SerializationException):
        backend.parse_raw(b"", media_type=MediaType.CSS)


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_iterable_annotation(
    backend_type: type[AbstractDTOBackend], field_definitions: FieldDefinitionsType
) -> None:
    ctx = BackendContext(ParsedType(List[DC]), field_definitions)
    backend = backend_type(ctx)
    parsed_type = ParsedType(backend.annotation)
    assert parsed_type.origin is list
    if backend_type is MsgspecDTOBackend:
        assert parsed_type.has_inner_subclass_of(Struct)

    if backend_type is PydanticDTOBackend:
        assert parsed_type.has_inner_subclass_of(BaseModel)


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_scalar_annotation(
    backend_type: type[AbstractDTOBackend], field_definitions: FieldDefinitionsType
) -> None:
    ctx = BackendContext(ParsedType(DC), field_definitions)
    backend = backend_type(ctx)
    if backend_type is MsgspecDTOBackend:
        assert ParsedType(backend.annotation).is_subclass_of(Struct)

    if backend_type is PydanticDTOBackend:
        assert ParsedType(backend.annotation).is_subclass_of(BaseModel)


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_populate_data_from_builtins(
    backend_type: type[AbstractDTOBackend], field_definitions: FieldDefinitionsType
) -> None:
    ctx = BackendContext(ParsedType(DC), field_definitions)
    backend = backend_type(ctx)
    data = backend.populate_data_from_builtins(DC, data=DESTRUCTURED)
    assert data == DC(a=1, b="b", c=[], nested=NestedDC(a=1, b="two"))


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_create_openapi_schema(
    backend_type: type[AbstractDTOBackend], field_definitions: FieldDefinitionsType
) -> None:
    ctx = BackendContext(ParsedType(DC), field_definitions)
    backend = backend_type(ctx)
    schemas: dict[str, Any] = {}
    ref = backend.create_openapi_schema(False, schemas)
    assert isinstance(ref, Reference)
    schema = schemas[ref.value]
    assert schema.properties["a"].type == "integer"
    assert schema.properties["b"].type == "string"
    assert schema.properties["c"].items.type == "integer"
    assert schema.properties["c"].type == "array"
    assert isinstance(nested := schema.properties["nested"], Reference)
    nested_schema = schemas[nested.value]
    assert nested_schema.properties["a"].type == "integer"
    assert nested_schema.properties["b"].type == "string"
