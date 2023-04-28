# ruff: noqa: UP006
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, List, Optional

import pytest
from msgspec import Struct, to_builtins
from pydantic import BaseModel

from litestar.dto.factory._backends import MsgspecDTOBackend, PydanticDTOBackend
from litestar.dto.factory._backends.abc import BackendContext
from litestar.dto.factory.types import FieldDefinition, NestedFieldDefinition
from litestar.dto.interface import ConnectionContext
from litestar.enums import MediaType
from litestar.exceptions import SerializationException
from litestar.openapi.spec.reference import Reference
from litestar.serialization import encode_json
from litestar.types.empty import Empty
from litestar.utils.signature import ParsedType

if TYPE_CHECKING:
    from typing import Any

    from litestar.dto.factory._backends import AbstractDTOBackend
    from litestar.dto.factory.types import FieldDefinitionsType


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
    nested_list: List[NestedDC]
    optional: str | None = None


DESTRUCTURED = {
    "a": 1,
    "b": "b",
    "c": [],
    "nested": {"a": 1, "b": "two"},
    "nested_list": [{"a": 1, "b": "two"}],
    "optional": None,
}
RAW = b'{"a":1,"b":"b","c":[],"nested":{"a":1,"b":"two"},"nested_list":[{"a":1,"b":"two"}],"optional":null}'
COLLECTION_RAW = (
    b'[{"a":1,"b":"b","c":[],"nested":{"a":1,"b":"two"},"nested_list":[{"a":1,"b":"two"}],"optional":null}]'
)
STRUCTURED = DC(a=1, b="b", c=[], nested=NestedDC(a=1, b="two"), nested_list=[NestedDC(a=1, b="two")], optional=None)


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
        "nested_list": NestedFieldDefinition(
            field_definition=FieldDefinition(name="nested_list", parsed_type=ParsedType(List[NestedDC]), default=Empty),
            nested_type=NestedDC,
            nested_field_definitions={
                "a": FieldDefinition(name="a", parsed_type=ParsedType(int), default=Empty),
                "b": FieldDefinition(name="b", parsed_type=ParsedType(str), default=Empty),
            },
        ),
        "optional": FieldDefinition(name="optional", parsed_type=ParsedType(Optional[str]), default=None),
    }


@pytest.fixture(name="backend", params=[MsgspecDTOBackend, PydanticDTOBackend])
def fx_backend(request: Any, field_definitions: FieldDefinitionsType) -> AbstractDTOBackend:
    ctx = BackendContext(ParsedType(DC), field_definitions, DC)
    return request.param(ctx)  # type:ignore[no-any-return]


@pytest.fixture(name="connection_context")
def fx_connection_context() -> ConnectionContext:
    return ConnectionContext(handler_id="handler_id", request_encoding_type="application/json")


def _destructure(model: BaseModel | Struct) -> dict[str, Any]:
    if isinstance(model, BaseModel):
        return model.dict()
    return to_builtins(model)  # type:ignore[no-any-return]


def test_backend_parse_raw_json(backend: AbstractDTOBackend, connection_context: ConnectionContext) -> None:
    assert (
        _destructure(
            backend.parse_raw(
                b'{"a":1,"nested":{"a":1,"b":"two"},"nested_list":[{"a":1,"b":"two"}]}', connection_context
            )
        )
        == DESTRUCTURED
    )


def test_backend_parse_raw_msgpack(backend: AbstractDTOBackend, connection_context: ConnectionContext) -> None:
    connection_context.request_encoding_type = MediaType.MESSAGEPACK  # type:ignore[misc]
    assert (
        _destructure(
            backend.parse_raw(
                b"\x83\xa1a\x01\xa6nested\x82\xa1a\x01\xa1b\xa3two\xabnested_list\x91\x82\xa1a\x01\xa1b\xa3two",
                connection_context,
            )
        )
        == DESTRUCTURED
    )


def test_backend_parse_unsupported_media_type(
    backend: AbstractDTOBackend, connection_context: ConnectionContext
) -> None:
    connection_context.request_encoding_type = MediaType.CSS  # type:ignore[misc]
    with pytest.raises(SerializationException):
        backend.parse_raw(b"", connection_context)


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_iterable_annotation(
    backend_type: type[AbstractDTOBackend], field_definitions: FieldDefinitionsType
) -> None:
    ctx = BackendContext(ParsedType(List[DC]), field_definitions, DC)
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
    ctx = BackendContext(ParsedType(DC), field_definitions, DC)
    backend = backend_type(ctx)
    if backend_type is MsgspecDTOBackend:
        assert ParsedType(backend.annotation).is_subclass_of(Struct)

    if backend_type is PydanticDTOBackend:
        assert ParsedType(backend.annotation).is_subclass_of(BaseModel)


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_populate_data_from_builtins(
    backend_type: type[AbstractDTOBackend], field_definitions: FieldDefinitionsType
) -> None:
    ctx = BackendContext(ParsedType(DC), field_definitions, DC)
    backend = backend_type(ctx)
    data = backend.populate_data_from_builtins(data=DESTRUCTURED)
    assert data == STRUCTURED


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_create_openapi_schema(
    backend_type: type[AbstractDTOBackend], field_definitions: FieldDefinitionsType
) -> None:
    ctx = BackendContext(ParsedType(DC), field_definitions, DC)
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


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_populate_data_from_raw(
    backend_type: type[AbstractDTOBackend],
    field_definitions: FieldDefinitionsType,
    connection_context: ConnectionContext,
) -> None:
    ctx = BackendContext(ParsedType(DC), field_definitions, DC)
    backend = backend_type(ctx)
    data = backend.populate_data_from_raw(RAW, connection_context)
    assert data == STRUCTURED


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_populate_collection_data_from_raw(
    backend_type: type[AbstractDTOBackend],
    field_definitions: FieldDefinitionsType,
    connection_context: ConnectionContext,
) -> None:
    ctx = BackendContext(ParsedType(List[DC]), field_definitions, DC)
    backend = backend_type(ctx)
    data = backend.populate_data_from_raw(COLLECTION_RAW, connection_context)
    assert data == [STRUCTURED]


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_encode_data(
    backend_type: type[AbstractDTOBackend],
    field_definitions: FieldDefinitionsType,
    connection_context: ConnectionContext,
) -> None:
    ctx = BackendContext(ParsedType(DC), field_definitions, DC)
    backend = backend_type(ctx)
    data = backend.encode_data(STRUCTURED, connection_context)
    assert encode_json(data) == RAW


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_encode_collection_data(
    backend_type: type[AbstractDTOBackend],
    field_definitions: FieldDefinitionsType,
    connection_context: ConnectionContext,
) -> None:
    ctx = BackendContext(ParsedType(List[DC]), field_definitions, DC)
    backend = backend_type(ctx)
    data = backend.encode_data([STRUCTURED], connection_context)
    assert encode_json(data) == COLLECTION_RAW
