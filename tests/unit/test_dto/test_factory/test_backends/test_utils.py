from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Any, Union

import pytest
from msgspec import Meta, Struct

from litestar.dto import DTOField
from litestar.dto._backend import _create_transfer_model_type_annotation, _should_mark_private
from litestar.dto._types import (
    CollectionType,
    CompositeType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TupleType,
    UnionType,
)
from litestar.dto.data_structures import DTOFieldDefinition
from litestar.typing import FieldDefinition


@dataclass
class DataModel:
    a: int
    b: str


class TransferModel(Struct):
    a: int
    b: str


def test_create_transfer_model_type_annotation_simple_type_without_nested_field_info() -> None:
    transfer_type = SimpleType(field_definition=FieldDefinition.from_annotation(int), nested_field_info=None)
    annotation = _create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == int


def test_create_transfer_model_type_annotation_simple_type_with_nested_field_info() -> None:
    transfer_type = SimpleType(
        field_definition=FieldDefinition.from_annotation(DataModel),
        nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
    )
    annotation = _create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == TransferModel


def test_create_transfer_model_type_annotation_collection_type_not_nested() -> None:
    transfer_type = CollectionType(
        field_definition=FieldDefinition.from_annotation(list[int]),
        inner_type=SimpleType(field_definition=FieldDefinition.from_annotation(int), nested_field_info=None),
        has_nested=False,
    )
    annotation = _create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == list[int]


def test_create_transfer_model_type_annotation_collection_type_nested() -> None:
    transfer_type = CollectionType(
        field_definition=FieldDefinition.from_annotation(list[DataModel]),
        inner_type=SimpleType(
            field_definition=FieldDefinition.from_annotation(DataModel),
            nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
        ),
        has_nested=True,
    )
    annotation = _create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == list[TransferModel]


def test_create_transfer_model_type_annotation_mapping_type_not_nested() -> None:
    transfer_type = MappingType(
        field_definition=FieldDefinition.from_annotation(dict[str, int]),
        key_type=SimpleType(field_definition=FieldDefinition.from_annotation(str), nested_field_info=None),
        value_type=SimpleType(field_definition=FieldDefinition.from_annotation(int), nested_field_info=None),
        has_nested=False,
    )
    annotation = _create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == dict[str, int]


def test_create_transfer_model_type_annotation_mapping_type_nested() -> None:
    transfer_type = MappingType(
        field_definition=FieldDefinition.from_annotation(dict[str, DataModel]),
        key_type=SimpleType(field_definition=FieldDefinition.from_annotation(str), nested_field_info=None),
        value_type=SimpleType(
            field_definition=FieldDefinition.from_annotation(DataModel),
            nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
        ),
        has_nested=True,
    )
    annotation = _create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == dict[str, TransferModel]


def test_create_transfer_model_type_annotation_tuple_type_not_nested() -> None:
    transfer_type = TupleType(
        field_definition=FieldDefinition.from_annotation(tuple[str, int]),
        inner_types=(
            SimpleType(field_definition=FieldDefinition.from_annotation(str), nested_field_info=None),
            SimpleType(field_definition=FieldDefinition.from_annotation(int), nested_field_info=None),
        ),
        has_nested=False,
    )
    annotation = _create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == tuple[str, int]


def test_create_transfer_model_type_annotation_tuple_type_nested() -> None:
    transfer_type = TupleType(
        field_definition=FieldDefinition.from_annotation(tuple[str, DataModel]),
        inner_types=(
            SimpleType(field_definition=FieldDefinition.from_annotation(str), nested_field_info=None),
            SimpleType(
                field_definition=FieldDefinition.from_annotation(DataModel),
                nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
            ),
        ),
        has_nested=True,
    )
    annotation = _create_transfer_model_type_annotation(transfer_type=transfer_type)
    assert annotation == tuple[str, TransferModel]


def test_create_transfer_model_type_annotation_unexpected_transfer_type() -> None:
    transfer_type = CompositeType(field_definition=FieldDefinition.from_annotation(Union[str, int]), has_nested=False)
    with pytest.raises(RuntimeError):
        _create_transfer_model_type_annotation(transfer_type=transfer_type)


def _transfer_type(field_definition: FieldDefinition) -> CompositeType | SimpleType:
    if field_definition.annotation is DataModel:
        return SimpleType(
            field_definition=field_definition,
            nested_field_info=NestedFieldInfo(model=TransferModel, field_definitions=()),
        )
    inner_types = tuple(_transfer_type(t) for t in field_definition.inner_types)
    if field_definition.is_union:
        return UnionType(field_definition=field_definition, inner_types=inner_types, has_nested=False)
    if field_definition.is_mapping:
        return MappingType(
            field_definition=field_definition, key_type=inner_types[0], value_type=inner_types[1], has_nested=False
        )
    if field_definition.is_tuple:
        return TupleType(field_definition=field_definition, inner_types=inner_types, has_nested=False)
    if field_definition.is_non_string_collection:
        return CollectionType(field_definition=field_definition, inner_type=inner_types[0], has_nested=False)
    return SimpleType(field_definition=field_definition, nested_field_info=None)


M5 = Meta(min_length=5)


@pytest.mark.parametrize(
    "annotation, passthrough_constraints, is_data_field, expected",
    [
        (list[Annotated[str, M5]], True, True, list[Annotated[str, M5]]),
        (
            dict[Annotated[str, M5], Annotated[int, Meta(ge=1)]],
            True,
            True,
            dict[Annotated[str, M5], Annotated[int, Meta(ge=1)]],
        ),
        (
            list[Annotated[DataModel, Meta(description="d")]],
            True,
            True,
            list[Annotated[TransferModel, Meta(description="d")]],
        ),
        (dict[Annotated[str, M5], Annotated[int, Meta(ge=1)]], False, True, dict[str, int]),
        (
            list[Annotated[int, Meta(min_length=1, description="d")]],
            True,
            False,
            list[Annotated[int, Meta(description="d")]],
        ),
        (list[Annotated[int, Meta(min_length=1)]], True, False, list[int]),
        (list[Annotated[str, M5]], True, False, list[Annotated[str, M5]]),
    ],
)
def test_create_transfer_model_type_annotation_member_meta(
    annotation: Any, passthrough_constraints: bool, is_data_field: bool, expected: Any
) -> None:
    transfer_type = _transfer_type(FieldDefinition.from_annotation(annotation))
    assert _create_transfer_model_type_annotation(transfer_type, passthrough_constraints, is_data_field) == expected


def test_should_mark_private_underscore_fields_private_true() -> None:
    assert (
        _should_mark_private(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(annotation=int, name="a", default=1),
                model_name="A",
                default_factory=None,
                dto_field=DTOField(),
            ),
            True,
        )
        is False
    )
    assert (
        _should_mark_private(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(annotation=int, name="_a", default=1),
                model_name="A",
                default_factory=None,
                dto_field=DTOField(),
            ),
            True,
        )
        is True
    )
    assert (
        _should_mark_private(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(annotation=int, name="_a", default=1),
                model_name="A",
                default_factory=None,
                dto_field=DTOField(mark="read-only"),
            ),
            True,
        )
        is False
    )


def test_should_mark_private_underscore_fields_private_false() -> None:
    assert (
        _should_mark_private(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(annotation=int, name="a", default=1),
                model_name="A",
                default_factory=None,
                dto_field=DTOField(),
            ),
            False,
        )
        is False
    )
    assert (
        _should_mark_private(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(annotation=int, name="_a", default=1),
                model_name="A",
                default_factory=None,
                dto_field=DTOField(),
            ),
            False,
        )
        is False
    )
    assert (
        _should_mark_private(
            DTOFieldDefinition.from_field_definition(
                field_definition=FieldDefinition.from_kwarg(annotation=int, name="_a", default=1),
                model_name="A",
                default_factory=None,
                dto_field=DTOField(mark="read-only"),
            ),
            False,
        )
        is False
    )
