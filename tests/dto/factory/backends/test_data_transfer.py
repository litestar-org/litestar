from __future__ import annotations

import inspect
from dataclasses import dataclass
from typing import TYPE_CHECKING, List

import pytest
from msgspec import Struct

from litestar.dto.factory._backends.data_transfer import create_kwarg, create_transfer_function
from litestar.dto.factory._backends.types import (
    FieldDefinitionsType,
    NestedFieldDefinition,
    TransferFieldDefinition,
)
from litestar.types.empty import Empty
from litestar.types.protocols import DataclassProtocol
from litestar.utils.helpers import get_fqdn
from litestar.utils.signature import ParsedType

if TYPE_CHECKING:
    from typing import Literal


@dataclass
class NestedDataModel(DataclassProtocol):
    """Nested data model"""

    c: int
    d: str


@dataclass
class DataModel(DataclassProtocol):
    """Data model

    Always interact with this model via the `model_type` fixture to ensure that we don't modify the state of the model
    between tests.
    """

    a: int
    b: str
    nested: NestedDataModel
    nested_list: list[NestedDataModel]


class NestedTransferModel(Struct):
    """Nested struct"""

    C: int
    d: str


class TransferModel(Struct):
    """Test struct

    Always interact with this struct via the `struct_type` fixture to ensure that we don't modify the state of the
    struct between tests.
    """

    A: int
    b: str
    nested: NestedTransferModel
    nested_list: list[NestedTransferModel]


@pytest.fixture(name="field_definitions")
def fx_field_definitions() -> FieldDefinitionsType:
    model_fqdn = get_fqdn(DataModel)
    nested_fqdn = get_fqdn(NestedDataModel)
    return {
        "a": TransferFieldDefinition(
            name="a", parsed_type=ParsedType(int), default=1, serialization_name="A", model_fqdn=model_fqdn
        ),
        "b": TransferFieldDefinition(name="b", parsed_type=ParsedType(str), default="2", model_fqdn=model_fqdn),
        "nested": NestedFieldDefinition(
            field_definition=TransferFieldDefinition(
                name="nested",
                parsed_type=ParsedType(NestedDataModel),
                default=Empty,
                model_fqdn=model_fqdn,
            ),
            nested_type=NestedDataModel,
            nested_field_definitions={
                "c": TransferFieldDefinition(
                    name="c", parsed_type=ParsedType(int), default=3, serialization_name="C", model_fqdn=nested_fqdn
                ),
                "d": TransferFieldDefinition(
                    name="d", parsed_type=ParsedType(str), default="4", model_fqdn=nested_fqdn
                ),
            },
            transfer_model=NestedTransferModel,
        ),
        "nested_list": NestedFieldDefinition(
            field_definition=TransferFieldDefinition(
                name="nested_list",
                parsed_type=ParsedType(List[NestedDataModel]),
                default=Empty,
                model_fqdn=model_fqdn,
            ),
            nested_type=NestedDataModel,
            nested_field_definitions={
                "c": TransferFieldDefinition(
                    name="c", parsed_type=ParsedType(int), default=3, serialization_name="C", model_fqdn=nested_fqdn
                ),
                "d": TransferFieldDefinition(
                    name="d", parsed_type=ParsedType(str), default="4", model_fqdn=nested_fqdn
                ),
            },
            transfer_model=NestedTransferModel,
        ),
    }


@pytest.fixture(name="model_type")
def fx_model_type() -> type[DataModel]:
    return type("_Model", (DataModel,), {})


@pytest.fixture(name="model_instance")
def fx_model_instance(model_type: type[DataModel]) -> DataModel:
    return model_type(a=1, b="2", nested=NestedDataModel(c=3, d="4"), nested_list=[NestedDataModel(c=3, d="4")])


@pytest.fixture(name="struct_type")
def fx_struct_type() -> type[TransferModel]:
    return type("_Struct", (TransferModel,), {})


@pytest.fixture(name="struct_instance")
def fx_struct_instance(struct_type: type[TransferModel]) -> TransferModel:
    return struct_type(
        A=1, b="2", nested=NestedTransferModel(C=3, d="4"), nested_list=[NestedTransferModel(C=3, d="4")]
    )


@pytest.mark.parametrize(
    ("field_definition", "direction", "expected"),
    [
        (
            TransferFieldDefinition(name="a", parsed_type=ParsedType(int), default=1, model_fqdn="module.Model"),
            "in",
            "a=source_instance.a",
        ),
        (
            TransferFieldDefinition(
                name="a", parsed_type=ParsedType(int), default=1, serialization_name="A", model_fqdn="module.Model"
            ),
            "in",
            "a=source_instance.A",
        ),
        (
            TransferFieldDefinition(name="a", parsed_type=ParsedType(int), default=1, model_fqdn="module.Model"),
            "out",
            "a=source_instance.a",
        ),
        (
            TransferFieldDefinition(
                name="a", parsed_type=ParsedType(int), default=1, serialization_name="A", model_fqdn="module.Model"
            ),
            "out",
            "A=source_instance.a",
        ),
    ],
)
def test_create_kwarg(
    field_definition: TransferFieldDefinition, direction: Literal["in", "out"], expected: str
) -> None:
    assert create_kwarg(field_definition, "source_instance", direction) == expected


def test_create_transfer_function_out(
    field_definitions: FieldDefinitionsType, struct_type: type[TransferModel], model_instance: DataModel
) -> None:
    transfer_function = create_transfer_function(field_definitions, struct_type, "out")
    assert inspect.getsourcelines(transfer_function)[0] == [
        (
            "def transfer(source_instance, destination_type=destination_type, tests_dto_factory_backends_test_data_transfer_"
            "DataModel_nested_function=tests_dto_factory_backends_test_data_transfer_DataModel_nested_function, tests_"
            "dto_factory_backends_test_data_transfer_DataModel_nested_list_function=tests_dto_factory_backends_test_"
            "data_transfer_DataModel_nested_list_function):"
        ),
        (
            "  return destination_type(A=source_instance.a, b=source_instance.b, nested=tests_dto_factory_backends_test_data_"
            "transfer_DataModel_nested_function(source_instance.nested), nested_list=[tests_dto_factory_backends_test_"
            "data_transfer_DataModel_nested_list_function(item) for item in source_instance.nested_list])"
        ),
    ]
    transferred_instance = transfer_function(model_instance)
    assert isinstance(transferred_instance, TransferModel)
    assert transferred_instance.A == 1
    assert transferred_instance.b == "2"
    assert isinstance(transferred_instance.nested, NestedTransferModel)
    assert transferred_instance.nested.C == 3
    assert transferred_instance.nested.d == "4"
    assert isinstance(transferred_instance.nested_list, list)
    assert len(transferred_instance.nested_list) == 1
    assert isinstance(transferred_instance.nested_list[0], NestedTransferModel)
    assert transferred_instance.nested_list[0].C == 3
    assert transferred_instance.nested_list[0].d == "4"


def test_create_transfer_function_in(
    field_definitions: FieldDefinitionsType,
    model_type: type[DataModel],
    struct_instance: TransferModel,
    model_instance: DataModel,
) -> None:
    transfer_function = create_transfer_function(field_definitions, model_type, "in")
    assert inspect.getsourcelines(transfer_function)[0] == [
        (
            "def transfer(source_instance, destination_type=destination_type, "
            "tests_dto_factory_backends_test_data_transfer_DataModel_nested_function=tests_dto_factory_backends_test_"
            "data_transfer_DataModel_nested_function, tests_dto_factory_backends_test_data_transfer_DataModel_nested_"
            "list_function=tests_dto_factory_backends_test_data_transfer_DataModel_nested_list_function):"
        ),
        (
            "  return destination_type(a=source_instance.A, b=source_instance.b, nested=tests_dto_factory_backends_test_data_"
            "transfer_DataModel_nested_function(source_instance.nested), nested_list=[tests_dto_factory_backends_test_"
            "data_transfer_DataModel_nested_list_function(item) for item in source_instance.nested_list])"
        ),
    ]
    transferred_instance = transfer_function(struct_instance)
    assert isinstance(transferred_instance, DataModel)
    assert transferred_instance.a == 1
    assert transferred_instance.b == "2"
    assert isinstance(transferred_instance.nested, NestedDataModel)
    assert transferred_instance.nested.c == 3
    assert transferred_instance.nested.d == "4"
    assert isinstance(transferred_instance.nested_list, list)
    assert len(transferred_instance.nested_list) == 1
    assert isinstance(transferred_instance.nested_list[0], NestedDataModel)
    assert transferred_instance.nested_list[0].c == 3
    assert transferred_instance.nested_list[0].d == "4"
