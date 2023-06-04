from __future__ import annotations

from typing import TYPE_CHECKING, Mapping, TypeVar

from msgspec import UNSET

from litestar.dto.factory._backends.types import (
    CollectionType,
    CompositeType,
    FieldDefinitionsType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TransferType,
    TupleType,
    UnionType,
)
from litestar.types.protocols import InstantiableCollection

from .predicates import should_skip_transfer

if TYPE_CHECKING:
    from typing import Any, Collection

    from litestar.dto.types import ForType
    from litestar.typing import ParsedType

T = TypeVar("T")

__all__ = ("transfer_data",)


def transfer_data(
    destination_type: type[T],
    source_data: Any | Collection[Any],
    field_definitions: FieldDefinitionsType,
    dto_for: ForType,
    parsed_type: ParsedType,
) -> T | InstantiableCollection[T]:
    """Create instance or iterable of instances of ``destination_type``.

    Args:
        destination_type: the model type received by the DTO on type narrowing.
        source_data: data that has been parsed and validated via the backend.
        field_definitions: model field definitions.
        dto_for: indicates whether the DTO is for the request body or response.
        parsed_type: the parsed type that represents the handler annotation for which the DTO is being applied.

    Returns:
        Data parsed into ``destination_type``.
    """
    if not parsed_type.is_subclass_of(str) and not parsed_type.is_mapping and parsed_type.is_collection:
        origin = parsed_type.instantiable_origin
        if not issubclass(origin, InstantiableCollection):  # pragma: no cover
            raise RuntimeError(f"Unexpected origin type '{parsed_type.instantiable_origin}', expected collection type")

        return origin(  # type:ignore[no-any-return]
            transfer_data(destination_type, item, field_definitions, dto_for, parsed_type.inner_types[0])
            for item in source_data
        )
    return transfer_instance_data(destination_type, source_data, field_definitions, dto_for)


def transfer_instance_data(
    destination_type: type[T], source_instance: Any, field_definitions: FieldDefinitionsType, dto_for: ForType
) -> T:
    """Create instance of ``destination_type`` with data from ``source_instance``.

    Args:
        destination_type: the model type received by the DTO on type narrowing.
        source_instance: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.
        dto_for: indicates whether the DTO is for the request body or response.

    Returns:
        Data parsed into ``model_type``.
    """
    unstructured_data = {}
    source_is_mapping = isinstance(source_instance, Mapping)

    if source_is_mapping:

        def has(source: Any, key: str) -> bool:
            return key in source

        def get(source: Any, key: str) -> Any:
            return source[key]

    else:

        def has(source: Any, key: str) -> bool:
            return hasattr(source, key)

        def get(source: Any, key: str) -> Any:
            return getattr(source, key)

    def filter_missing(value: Any) -> bool:
        return value is UNSET

    for field_definition in field_definitions:
        source_name = field_definition.serialization_name if dto_for == "data" else field_definition.name

        if should_skip_transfer(dto_for, field_definition, has(source_instance, source_name)):
            continue

        transfer_type = field_definition.transfer_type
        destination_name = field_definition.name if dto_for == "data" else field_definition.serialization_name
        source_value = get(source_instance, source_name)

        if field_definition.is_partial and dto_for == "data" and filter_missing(source_value):
            continue

        unstructured_data[destination_name] = transfer_type_data(
            source_value, transfer_type, dto_for, nested_as_dict=destination_type is dict
        )
    return destination_type(**unstructured_data)


def transfer_type_data(
    source_value: Any, transfer_type: TransferType, dto_for: ForType, nested_as_dict: bool = False
) -> Any:
    if isinstance(transfer_type, SimpleType) and transfer_type.nested_field_info:
        if nested_as_dict:
            dest_type = dict
        else:
            dest_type = (
                transfer_type.parsed_type.annotation if dto_for == "data" else transfer_type.nested_field_info.model
            )

        return transfer_nested_simple_type_data(dest_type, transfer_type.nested_field_info, dto_for, source_value)
    if isinstance(transfer_type, UnionType) and transfer_type.has_nested:
        return transfer_nested_union_type_data(transfer_type, dto_for, source_value)
    if isinstance(transfer_type, CollectionType):
        if transfer_type.has_nested:
            return transfer_nested_collection_type_data(
                transfer_type.parsed_type.origin, transfer_type, dto_for, source_value
            )
        return transfer_type.parsed_type.origin(source_value)
    return source_value


def transfer_nested_collection_type_data(
    origin_type: type[Any], transfer_type: CollectionType, dto_for: ForType, source_value: Any
) -> Any:
    return origin_type(transfer_type_data(item, transfer_type.inner_type, dto_for) for item in source_value)


def transfer_nested_simple_type_data(
    destination_type: type[Any], nested_field_info: NestedFieldInfo, dto_for: ForType, source_value: Any
) -> Any:
    return transfer_instance_data(destination_type, source_value, nested_field_info.field_definitions, dto_for)


def transfer_nested_union_type_data(transfer_type: UnionType, dto_for: ForType, source_value: Any) -> Any:
    for inner_type in transfer_type.inner_types:
        if isinstance(inner_type, CompositeType):
            raise RuntimeError("Composite inner types not (yet) supported for nested unions.")

        if inner_type.nested_field_info and isinstance(
            source_value,
            inner_type.nested_field_info.model if dto_for == "data" else inner_type.parsed_type.annotation,
        ):
            return transfer_instance_data(
                inner_type.parsed_type.annotation if dto_for == "data" else inner_type.nested_field_info.model,
                source_value,
                inner_type.nested_field_info.field_definitions,
                dto_for,
            )
    return source_value


def create_transfer_model_type_annotation(transfer_type: TransferType) -> Any:
    """Create a type annotation for a transfer model.

    Uses the parsed type that originates from the data model and the transfer model generated to represent a nested
    type to reconstruct the type annotation for the transfer model.
    """
    if isinstance(transfer_type, SimpleType):
        if transfer_type.nested_field_info:
            return transfer_type.nested_field_info.model
        return transfer_type.parsed_type.annotation

    if isinstance(transfer_type, CollectionType):
        return create_transfer_model_collection_type(transfer_type)

    if isinstance(transfer_type, MappingType):
        return create_transfer_model_mapping_type(transfer_type)

    if isinstance(transfer_type, TupleType):
        return create_transfer_model_tuple_type(transfer_type)

    if isinstance(transfer_type, UnionType):
        return create_transfer_model_union_type(transfer_type)

    raise RuntimeError(f"Unexpected transfer type: {type(transfer_type)}")


def create_transfer_model_collection_type(transfer_type: CollectionType) -> Any:
    generic_collection_type = transfer_type.parsed_type.safe_generic_origin
    inner_type = create_transfer_model_type_annotation(transfer_type.inner_type)
    if transfer_type.parsed_type.origin is tuple:
        return generic_collection_type[inner_type, ...]
    return generic_collection_type[inner_type]


def create_transfer_model_tuple_type(transfer_type: TupleType) -> Any:
    inner_types = tuple(create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.parsed_type.safe_generic_origin[inner_types]


def create_transfer_model_union_type(transfer_type: UnionType) -> Any:
    inner_types = tuple(create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.parsed_type.safe_generic_origin[inner_types]


def create_transfer_model_mapping_type(transfer_type: MappingType) -> Any:
    key_type = create_transfer_model_type_annotation(transfer_type.key_type)
    value_type = create_transfer_model_type_annotation(transfer_type.value_type)
    return transfer_type.parsed_type.safe_generic_origin[key_type, value_type]
