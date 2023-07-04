from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Dict, Generator, List, Tuple, Union

import pytest

from litestar.dto.factory import DTOConfig, DTOField
from litestar.dto.factory._backends.abc import AbstractDTOBackend, BackendContext
from litestar.dto.factory._backends.types import (
    CollectionType,
    CompositeType,
    MappingType,
    SimpleType,
    TupleType,
    UnionType,
)
from litestar.dto.factory.data_structures import DTOFieldDefinition
from litestar.dto.types import ForType
from litestar.types.empty import Empty
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from typing import AbstractSet

    from litestar.dto.factory._backends.types import FieldDefinitionsType, TransferType
    from litestar.dto.interface import ConnectionContext


@dataclass
class Model:
    a: int
    b: str


@dataclass
class Model2:
    c: int
    d: str


@pytest.fixture(name="data_model_type")
def fx_data_model_type() -> type[Model]:
    return type("Model", (Model,), {})


@pytest.fixture(name="data_model")
def fx_data_model(data_model_type: type[Model]) -> Model:
    return data_model_type(a=1, b="2")


@pytest.fixture(name="field_definitions")
def fx_field_definitions(data_model_type: type[Model]) -> list[DTOFieldDefinition]:
    return [
        DTOFieldDefinition.from_field_definition(
            field_definition=FieldDefinition.from_kwarg(
                annotation=int,
                name="a",
                default=Empty,
            ),
            default_factory=None,
            dto_field=DTOField(),
            unique_model_name="some_module.SomeModel",
            dto_for=None,
        ),
        DTOFieldDefinition.from_field_definition(
            field_definition=FieldDefinition.from_kwarg(
                annotation=str,
                name="b",
                default=Empty,
            ),
            default_factory=None,
            dto_field=DTOField(),
            unique_model_name="some_module.SomeModel",
            dto_for=None,
        ),
    ]


@pytest.fixture(name="context")
def fx_context(data_model_type: type[Model], field_definitions: list[DTOFieldDefinition]) -> BackendContext:
    def _generator(_: Any) -> Generator[DTOFieldDefinition, None, None]:
        yield from field_definitions

    return BackendContext(
        dto_config=DTOConfig(),
        dto_for="data",
        field_definition=FieldDefinition.from_annotation(data_model_type),
        field_definition_generator=_generator,
        is_nested_field_predicate=lambda field_definition: field_definition.is_subclass_of((Model, Model2)),
        model_type=data_model_type,
        wrapper_attribute_name=None,
    )


@pytest.fixture(name="backend")
def fx_backend(context: BackendContext) -> AbstractDTOBackend:
    class _Backend(AbstractDTOBackend[Any]):
        def create_transfer_model_type(self, unique_name: str, field_definitions: FieldDefinitionsType) -> type[Any]:
            """Create a model for data transfer.

            Args:
            unique_name: name for the type that should be unique across all transfer types.
            field_definitions: field definitions for the container type.

            Returns:
            A ``BackendT`` class.
            """
            return Model

        def parse_raw(self, raw: bytes, connection_context: ConnectionContext) -> Any:
            """Parse raw bytes into transfer model type.

            Args:
            raw: bytes
            connection_context: Information about the active connection.

            Returns:
            The raw bytes parsed into transfer model type.
            """
            return None

        def parse_builtins(self, builtins: Any, connection_context: ConnectionContext) -> Any:
            """Parse builtin types into transfer model type.

            Args:
            builtins: Builtin type.
            connection_context: Information about the active connection.

            Returns:
            The builtin type parsed into transfer model type.
            """
            return None

    return _Backend(context)


def create_transfer_type(
    backend: AbstractDTOBackend,
    field_definition: FieldDefinition,
    exclude: AbstractSet[str] | None = None,
    field_name: str = "name",
    unique_name: str = "some_module.SomeModel.name",
    nested_depth: int = 0,
) -> TransferType:
    return backend._create_transfer_type(field_definition, exclude or set(), field_name, unique_name, nested_depth)


@pytest.mark.parametrize(
    ("field_definition", "should_have_nested", "has_nested_field_info"),
    [
        (FieldDefinition.from_annotation(Union[Model, None]), True, (True, False)),
        (FieldDefinition.from_annotation(Union[Model, str]), True, (True, False)),
        (FieldDefinition.from_annotation(Union[Model, int]), True, (True, False)),
        (FieldDefinition.from_annotation(Union[Model, Model2]), True, (True, True)),
        (FieldDefinition.from_annotation(Union[int, str]), False, (False, False)),
    ],
)
def test_create_transfer_type_union(
    field_definition: FieldDefinition,
    should_have_nested: bool,
    has_nested_field_info: tuple[bool, ...],
    backend: AbstractDTOBackend,
) -> None:
    transfer_type = create_transfer_type(backend, field_definition)
    assert isinstance(transfer_type, UnionType)
    assert transfer_type.has_nested is should_have_nested
    inner_types = transfer_type.inner_types
    assert len(inner_types) == len(transfer_type.field_definition.inner_types)
    for inner_type, has_nested in zip(inner_types, has_nested_field_info):
        assert isinstance(inner_type, SimpleType)
        assert bool(inner_type.nested_field_info) is has_nested


@pytest.mark.parametrize(
    ("field_definition", "should_have_nested", "has_nested_field_info"),
    [
        (FieldDefinition.from_annotation(Tuple[Model, None]), True, (True, False)),
        (FieldDefinition.from_annotation(Tuple[Model, str]), True, (True, False)),
        (FieldDefinition.from_annotation(Tuple[Model, int]), True, (True, False)),
        (FieldDefinition.from_annotation(Tuple[Model, Model2]), True, (True, True)),
        (FieldDefinition.from_annotation(Tuple[int, str]), False, (False, False)),
        (FieldDefinition.from_annotation(Tuple[Model, ...]), True, (True,)),
        (FieldDefinition.from_annotation(Tuple[int, ...]), False, (False,)),
    ],
)
def test_create_transfer_type_tuple(
    field_definition: FieldDefinition,
    should_have_nested: bool,
    has_nested_field_info: tuple[bool, ...],
    backend: AbstractDTOBackend,
) -> None:
    transfer_type = create_transfer_type(backend, field_definition)
    assert isinstance(transfer_type, CompositeType)
    assert transfer_type.has_nested is should_have_nested
    if field_definition.inner_types[-1].annotation is Ellipsis:
        assert isinstance(transfer_type, CollectionType)
        inner_type = transfer_type.inner_type
        assert isinstance(inner_type, SimpleType)
        assert bool(inner_type.nested_field_info) is has_nested_field_info[0]
    else:
        assert isinstance(transfer_type, TupleType)
        inner_types = transfer_type.inner_types
        assert len(inner_types) == len(transfer_type.field_definition.inner_types)
        for inner_type, has_nested in zip(inner_types, has_nested_field_info):
            assert isinstance(inner_type, SimpleType)
            assert bool(inner_type.nested_field_info) is has_nested


@pytest.mark.parametrize(
    ("field_definition", "should_have_nested", "has_nested_field_info"),
    [
        (FieldDefinition.from_annotation(Dict[Model, None]), True, (True, False)),
        (FieldDefinition.from_annotation(Dict[Model, str]), True, (True, False)),
        (FieldDefinition.from_annotation(Dict[Model, int]), True, (True, False)),
        (FieldDefinition.from_annotation(Dict[Model, Model2]), True, (True, True)),
        (FieldDefinition.from_annotation(Dict[int, str]), False, (False, False)),
    ],
)
def test_create_transfer_type_mapping(
    field_definition: FieldDefinition,
    should_have_nested: bool,
    has_nested_field_info: tuple[bool, ...],
    backend: AbstractDTOBackend,
) -> None:
    transfer_type = create_transfer_type(backend, field_definition)
    assert isinstance(transfer_type, MappingType)
    assert transfer_type.has_nested is should_have_nested
    key_type = transfer_type.key_type
    value_type = transfer_type.value_type
    for inner_type, has_nested in zip((key_type, value_type), has_nested_field_info):
        assert isinstance(inner_type, SimpleType)
        assert bool(inner_type.nested_field_info) is has_nested


@pytest.mark.parametrize(
    ("field_definition", "should_have_nested", "has_nested_field_info"),
    [
        (FieldDefinition.from_annotation(List[Model]), True, True),
        (FieldDefinition.from_annotation(List[int]), False, False),
    ],
)
def test_create_transfer_type_collection(
    field_definition: FieldDefinition,
    should_have_nested: bool,
    has_nested_field_info: bool,
    backend: AbstractDTOBackend,
) -> None:
    transfer_type = create_transfer_type(backend, field_definition)
    assert isinstance(transfer_type, CollectionType)
    assert transfer_type.has_nested is should_have_nested
    inner_type = transfer_type.inner_type
    assert isinstance(inner_type, SimpleType)
    assert bool(inner_type.nested_field_info) is has_nested_field_info


def test_create_collection_type_nested_union(backend: AbstractDTOBackend) -> None:
    field_definition = FieldDefinition.from_annotation(List[Union[Model, Model2]])
    transfer_type = create_transfer_type(backend, field_definition)
    assert isinstance(transfer_type, CollectionType)
    assert transfer_type.has_nested is True
    inner_type = transfer_type.inner_type
    assert isinstance(inner_type, UnionType)
    assert inner_type.has_nested is True
    inner_types = inner_type.inner_types
    assert len(inner_types) == len(inner_type.field_definition.inner_types)
    for inner_type in inner_types:
        assert isinstance(inner_type, SimpleType)
        assert bool(inner_type.nested_field_info)


@pytest.mark.parametrize("dto_for", ["data", "return"])
def test_parse_model_respects_field_definition_dto_for(
    dto_for: ForType, backend: AbstractDTOBackend, field_definitions: list[DTOFieldDefinition]
) -> None:
    object.__setattr__(field_definitions[0], "dto_for", "data")
    object.__setattr__(field_definitions[1], "dto_for", "return")
    backend.context.dto_for = dto_for  # type:ignore[misc]
    backend.context.field_definition_generator = lambda _: iter(field_definitions)  # type: ignore
    transfer_field_defs = backend.parse_model(None, exclude=set())
    assert len(transfer_field_defs) == 1
    assert transfer_field_defs[0].dto_for == dto_for
