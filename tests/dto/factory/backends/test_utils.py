from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple, Union

import pytest
from msgspec import Struct

from litestar.dto.factory._backends.types import (
    CollectionType,
    CompositeType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TupleType,
    UnionType,
)
from litestar.dto.factory._backends.utils import create_transfer_model_type_annotation, transfer_nested_union_type_data
from litestar.utils.signature import ParsedType


@dataclass
class DataModel:
    a: int
    b: str


class TransferModel(Struct):
    a: int
    b: str


def test_transfer_nested_union_type_data_raises_runtime_error_for_complex_union() -> None:
    transfer_type = UnionType(
        parsed_type=ParsedType(Union[List[DataModel], int]),
        inner_types=(
            CollectionType(
                parsed_type=ParsedType(List[DataModel]),
                inner_type=SimpleType(
                    parsed_type=ParsedType(DataModel),
                    nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
                ),
                has_nested=True,
            ),
            SimpleType(parsed_type=ParsedType(int), nested_field_info=None),
        ),
        has_nested=True,
    )
    with pytest.raises(RuntimeError):
        transfer_nested_union_type_data(transfer_type=transfer_type, dto_for="data", source_value=1)


def test_create_transfer_model_type_annotation_simple_type_without_nested_field_info() -> None:
    transfer_type = SimpleType(parsed_type=ParsedType(int), nested_field_info=None)
    annotation = create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == int


def test_create_transfer_model_type_annotation_simple_type_with_nested_field_info() -> None:
    transfer_type = SimpleType(
        parsed_type=ParsedType(DataModel),
        nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
    )
    annotation = create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == TransferModel


def test_create_transfer_model_type_annotation_collection_type_not_nested() -> None:
    transfer_type = CollectionType(
        parsed_type=ParsedType(List[int]),
        inner_type=SimpleType(parsed_type=ParsedType(int), nested_field_info=None),
        has_nested=False,
    )
    annotation = create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == List[int]


def test_create_transfer_model_type_annotation_collection_type_nested() -> None:
    transfer_type = CollectionType(
        parsed_type=ParsedType(List[DataModel]),
        inner_type=SimpleType(
            parsed_type=ParsedType(DataModel),
            nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
        ),
        has_nested=True,
    )
    annotation = create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == List[TransferModel]


def test_create_transfer_model_type_annotation_mapping_type_not_nested() -> None:
    transfer_type = MappingType(
        parsed_type=ParsedType(Dict[str, int]),
        key_type=SimpleType(parsed_type=ParsedType(str), nested_field_info=None),
        value_type=SimpleType(parsed_type=ParsedType(int), nested_field_info=None),
        has_nested=False,
    )
    annotation = create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == Dict[str, int]


def test_create_transfer_model_type_annotation_mapping_type_nested() -> None:
    transfer_type = MappingType(
        parsed_type=ParsedType(Dict[str, DataModel]),
        key_type=SimpleType(parsed_type=ParsedType(str), nested_field_info=None),
        value_type=SimpleType(
            parsed_type=ParsedType(DataModel),
            nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
        ),
        has_nested=True,
    )
    annotation = create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == Dict[str, TransferModel]


def test_create_transfer_model_type_annotation_tuple_type_not_nested() -> None:
    transfer_type = TupleType(
        parsed_type=ParsedType(Tuple[str, int]),
        inner_types=(
            SimpleType(parsed_type=ParsedType(str), nested_field_info=None),
            SimpleType(parsed_type=ParsedType(int), nested_field_info=None),
        ),
        has_nested=False,
    )
    annotation = create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == Tuple[str, int]


def test_create_transfer_model_type_annotation_tuple_type_nested() -> None:
    transfer_type = TupleType(
        parsed_type=ParsedType(Tuple[str, DataModel]),
        inner_types=(
            SimpleType(parsed_type=ParsedType(str), nested_field_info=None),
            SimpleType(
                parsed_type=ParsedType(DataModel),
                nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
            ),
        ),
        has_nested=True,
    )
    annotation = create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == Tuple[str, TransferModel]


def test_create_transfer_model_type_annotation_unexpected_transfer_type() -> None:
    transfer_type = CompositeType(parsed_type=ParsedType(Union[str, int]), has_nested=False)
    with pytest.raises(RuntimeError):
        create_transfer_model_type_annotation(transfer_type=transfer_type)
