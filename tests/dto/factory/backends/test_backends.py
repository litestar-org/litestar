# ruff: noqa: UP006,UP007
from __future__ import annotations

from dataclasses import dataclass, field
from types import ModuleType
from typing import TYPE_CHECKING, Callable, List, Optional

import pytest
from msgspec import Struct, to_builtins
from pydantic import BaseModel

from litestar.dto.factory import DTOConfig
from litestar.dto.factory._backends import MsgspecDTOBackend, PydanticDTOBackend
from litestar.dto.factory._backends.abc import BackendContext
from litestar.dto.factory._backends.types import NestedFieldDefinition
from litestar.dto.factory.stdlib.dataclass import DataclassDTO
from litestar.dto.interface import ConnectionContext
from litestar.enums import MediaType
from litestar.exceptions import SerializationException
from litestar.openapi.spec.reference import Reference
from litestar.serialization import encode_json
from litestar.utils.signature import ParsedType

if TYPE_CHECKING:
    from typing import Any

    from litestar.dto.factory._backends import AbstractDTOBackend


@dataclass
class NestedDC:
    a: int
    b: str


@dataclass
class DC:
    a: int
    nested: NestedDC
    nested_list: List[NestedDC]
    b: str = field(default="b")
    c: List[int] = field(default_factory=list)
    optional: Optional[str] = None


DESTRUCTURED = {
    "a": 1,
    "b": "b",
    "c": [],
    "nested": {"a": 1, "b": "two"},
    "nested_list": [{"a": 1, "b": "two"}],
    "optional": None,
}
RAW = b'{"a":1,"nested":{"a":1,"b":"two"},"nested_list":[{"a":1,"b":"two"}],"b":"b","c":[],"optional":null}'
COLLECTION_RAW = (
    b'[{"a":1,"nested":{"a":1,"b":"two"},"nested_list":[{"a":1,"b":"two"}],"b":"b","c":[],"optional":null}]'
)
STRUCTURED = DC(a=1, b="b", c=[], nested=NestedDC(a=1, b="two"), nested_list=[NestedDC(a=1, b="two")], optional=None)


@pytest.fixture(name="backend", params=[MsgspecDTOBackend, PydanticDTOBackend])
def fx_backend(request: Any) -> AbstractDTOBackend:
    ctx = BackendContext(
        DTOConfig(),
        "data",
        ParsedType(DC),
        DataclassDTO.generate_field_definitions,
        DataclassDTO.detect_nested_field,
        DC,
    )
    return request.param(ctx)  # type:ignore[no-any-return]


@pytest.fixture(name="connection_context")
def fx_connection_context() -> ConnectionContext:
    return ConnectionContext(handler_id="handler_id", request_encoding_type="application/json")


@pytest.fixture(name="backend_context")
def fx_backend_context() -> BackendContext:
    return BackendContext(
        DTOConfig(),
        "data",
        ParsedType(DC),
        DataclassDTO.generate_field_definitions,
        DataclassDTO.detect_nested_field,
        DC,
    )


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
def test_backend_iterable_annotation(backend_type: type[AbstractDTOBackend], backend_context: BackendContext) -> None:
    backend_context.parsed_type = ParsedType(List[DC])  # type:ignore[misc]
    backend = backend_type(backend_context)
    parsed_type = ParsedType(backend.annotation)
    assert parsed_type.origin is list
    if backend_type is MsgspecDTOBackend:
        assert parsed_type.has_inner_subclass_of(Struct)

    if backend_type is PydanticDTOBackend:
        assert parsed_type.has_inner_subclass_of(BaseModel)


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_scalar_annotation(backend_type: type[AbstractDTOBackend], backend_context: BackendContext) -> None:
    backend = backend_type(backend_context)
    if backend_type is MsgspecDTOBackend:
        assert ParsedType(backend.annotation).is_subclass_of(Struct)

    if backend_type is PydanticDTOBackend:
        assert ParsedType(backend.annotation).is_subclass_of(BaseModel)


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_populate_data_from_builtins(
    backend_type: type[AbstractDTOBackend], backend_context: BackendContext
) -> None:
    backend = backend_type(backend_context)
    data = backend.populate_data_from_builtins(data=DESTRUCTURED)
    assert data == STRUCTURED


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_create_openapi_schema(backend_type: type[AbstractDTOBackend], backend_context: BackendContext) -> None:
    backend = backend_type(backend_context)
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
    backend_type: type[AbstractDTOBackend], backend_context: BackendContext, connection_context: ConnectionContext
) -> None:
    backend = backend_type(backend_context)
    data = backend.populate_data_from_raw(RAW, connection_context)
    assert data == STRUCTURED


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_populate_collection_data_from_raw(
    backend_type: type[AbstractDTOBackend], backend_context: BackendContext, connection_context: ConnectionContext
) -> None:
    backend_context.parsed_type = ParsedType(List[DC])  # type:ignore[misc]
    backend = backend_type(backend_context)
    data = backend.populate_data_from_raw(COLLECTION_RAW, connection_context)
    assert data == [STRUCTURED]


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_encode_data(
    backend_type: type[AbstractDTOBackend], backend_context: BackendContext, connection_context: ConnectionContext
) -> None:
    backend = backend_type(backend_context)
    data = backend.encode_data(STRUCTURED, connection_context)
    assert encode_json(data) == RAW


@pytest.mark.parametrize("backend_type", [MsgspecDTOBackend, PydanticDTOBackend])
def test_backend_encode_collection_data(
    backend_type: type[AbstractDTOBackend], connection_context: ConnectionContext
) -> None:
    ctx = BackendContext(
        DTOConfig(),
        "data",
        ParsedType(List[DC]),
        DataclassDTO.generate_field_definitions,
        DataclassDTO.detect_nested_field,
        DC,
    )
    backend = backend_type(ctx)
    data = backend.encode_data([STRUCTURED], connection_context)
    assert encode_json(data) == COLLECTION_RAW


def test_parse_model_nested_exclude(create_module: Callable[[str], ModuleType]) -> None:
    module = create_module(
        """
from dataclasses import dataclass
from typing import List

from litestar.dto.factory.stdlib.dataclass import DataclassDTO

@dataclass
class NestedNestedModel:
    e: int
    f: int

@dataclass
class NestedModel:
    c: int
    d: List[NestedNestedModel]

@dataclass
class Model:
    a: int
    b: NestedModel

dto_type = DataclassDTO[Model]
    """
    )
    config = DTOConfig(max_nested_depth=2, exclude={"a", "b.c", "b.d.e"})
    ctx = BackendContext(
        dto_config=config,
        dto_for="data",
        parsed_type=ParsedType(module.Model),
        field_definition_generator=DataclassDTO.generate_field_definitions,
        nested_field_detector=DataclassDTO.detect_nested_field,
        model_type=module.Model,
    )
    parsed = MsgspecDTOBackend(context=ctx).parsed_field_definitions
    assert "a" not in parsed
    assert "b" in parsed
    assert isinstance(parsed["b"], NestedFieldDefinition)
    assert "c" not in parsed["b"].nested_field_definitions
    assert "d" in parsed["b"].nested_field_definitions
    assert isinstance(parsed["b"].nested_field_definitions["d"], NestedFieldDefinition)
    assert "e" not in parsed["b"].nested_field_definitions["d"].nested_field_definitions
    assert "f" in parsed["b"].nested_field_definitions["d"].nested_field_definitions
