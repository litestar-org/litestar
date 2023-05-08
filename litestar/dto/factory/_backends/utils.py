from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, TypeVar, cast

from typing_extensions import get_origin

from litestar.dto.factory import Mark

from .types import CollectionType, MappingType, SimpleType, TransferType, TupleType, UnionType

if TYPE_CHECKING:
    from typing import AbstractSet, Any, Collection, Iterable

    from msgspec import Struct

    from litestar.dto.factory.types import FieldDefinition, RenameStrategy
    from litestar.dto.types import ForType

    from .types import FieldDefinitionsType

__all__ = (
    "RenameStrategies",
    "build_annotation_for_backend",
    "create_transfer_model_type_annotation",
    "should_exclude_field",
    "_transfer_data",
)

T = TypeVar("T")


def build_annotation_for_backend(annotation: Any, model: type[T]) -> type[T] | type[Iterable[T]]:
    """A helper to re-build a generic outer type with new inner type.

    Args:
        annotation: The original annotation on the handler signature
        model: The data container type

    Returns:
        Annotation with new inner type if applicable.
    """
    origin = get_origin(annotation)
    if not origin:
        return model
    try:
        return origin[model]  # type:ignore[no-any-return]
    except TypeError:  # pragma: no cover
        return annotation.copy_with((model,))  # type:ignore[no-any-return]


def should_exclude_field(field_definition: FieldDefinition, exclude: AbstractSet[str], dto_for: ForType) -> bool:
    """Returns ``True`` where a field should be excluded from data transfer.

    Args:
        field_definition: defined DTO field
        exclude: names of fields to exclude
        dto_for: indicates whether the DTO is for the request body or response.

    Returns:
        ``True`` if the field should not be included in any data transfer.
    """
    field_name = field_definition.name
    dto_field = field_definition.dto_field
    excluded = field_name in exclude
    private = dto_field and dto_field.mark is Mark.PRIVATE
    read_only_for_write = dto_for == "data" and dto_field and dto_field.mark is Mark.READ_ONLY
    return bool(excluded or private or read_only_for_write)


class RenameStrategies:
    """Useful renaming strategies than be used with :class:`DTOConfig`"""

    def __init__(self, renaming_strategy: RenameStrategy) -> None:
        self.renaming_strategy = renaming_strategy

    def __call__(self, field_name: str) -> str:
        if not isinstance(self.renaming_strategy, str):
            return self.renaming_strategy(field_name)

        return cast(str, getattr(self, self.renaming_strategy)(field_name))

    @staticmethod
    def upper(field_name: str) -> str:
        return field_name.upper()

    @staticmethod
    def lower(field_name: str) -> str:
        return field_name.lower()

    @staticmethod
    def camel(field_name: str) -> str:
        return RenameStrategies._camelize(field_name)

    @staticmethod
    def pascal(field_name: str) -> str:
        return RenameStrategies._camelize(field_name, capitalize_first_letter=True)

    @staticmethod
    def _camelize(string: str, capitalize_first_letter: bool = False) -> str:
        """Convert a string to camel case.

        Args:
            string (str): The string to convert
            capitalize_first_letter (bool): Default is False, a True value will convert to PascalCase
        Returns:
            str: The string converted to camel case or Pascal case
        """
        return "".join(
            word if index == 0 and not capitalize_first_letter else word.capitalize()
            for index, word in enumerate(string.split("_"))
        )


def _transfer_instance_data(
    destination_type: type[T], source_instance: Struct, field_definitions: FieldDefinitionsType, dto_for: ForType
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
    for field_definition in field_definitions.values():
        transfer_type = field_definition.transfer_type
        source_name = (
            field_definition.serialization_name or field_definition.name if dto_for == "data" else field_definition.name
        )
        destination_name = (
            field_definition.name if dto_for == "data" else field_definition.serialization_name or field_definition.name
        )
        source_value = getattr(source_instance, source_name)
        if isinstance(transfer_type, SimpleType) and transfer_type.transfer_model:
            unstructured_data[destination_name] = _transfer_instance_data(
                transfer_type.parsed_type.annotation if dto_for == "data" else transfer_type.transfer_model.model,
                source_value,
                transfer_type.transfer_model.field_definitions,
                dto_for,
            )
        elif isinstance(transfer_type, UnionType) and transfer_type.has_nested:
            for inner_type in transfer_type.inner_types:
                if (
                    isinstance(inner_type, SimpleType)
                    and inner_type.transfer_model
                    and isinstance(
                        source_value,
                        inner_type.transfer_model.model if dto_for == "data" else inner_type.parsed_type.annotation,
                    )
                ):
                    unstructured_data[destination_name] = _transfer_instance_data(
                        inner_type.parsed_type.annotation if dto_for == "data" else inner_type.transfer_model.model,
                        source_value,
                        inner_type.transfer_model.field_definitions,
                        dto_for,
                    )
        elif isinstance(transfer_type, CollectionType) and transfer_type.has_nested:
            if field_definition.parsed_type.origin is None:  # pragma: no cover
                raise RuntimeError("Unexpected origin value for collection type.")

            if not isinstance(transfer_type.inner_type, SimpleType):
                raise RuntimeError("Compound inner types not yet supported")

            if transfer_type.inner_type.transfer_model is None:
                raise RuntimeError("Inner type expected to have transfer model")

            dest_type = (
                transfer_type.inner_type.parsed_type.annotation
                if dto_for == "data"
                else transfer_type.inner_type.transfer_model.model
            )
            unstructured_data[destination_name] = field_definition.parsed_type.origin(
                _transfer_instance_data(
                    dest_type, item, transfer_type.inner_type.transfer_model.field_definitions, dto_for
                )
                for item in source_value
            )
        else:
            unstructured_data[destination_name] = source_value

    return destination_type(**unstructured_data)


def _transfer_data(
    destination_type: type[T],
    source_data: Any | Collection[Any],
    field_definitions: FieldDefinitionsType,
    dto_for: ForType = "data",
) -> T | Collection[T]:
    """Create instance or iterable of instances of ``destination_type``.

    Args:
        destination_type: the model type received by the DTO on type narrowing.
        source_data: data that has been parsed and validated via the backend.
        field_definitions: model field definitions.
        dto_for: indicates whether the DTO is for the request body or response.

    Returns:
        Data parsed into ``destination_type``.
    """
    if isinstance(source_data, CollectionsCollection):
        return type(source_data)(
            _transfer_data(destination_type, item, field_definitions, dto_for)  # type:ignore[call-arg]
            for item in source_data
        )
    return _transfer_instance_data(destination_type, source_data, field_definitions, dto_for)


def create_transfer_model_type_annotation(transfer_type: TransferType) -> Any:
    """Create a type annotation for a transfer model.

    Uses the parsed type that originates from the data model and the transfer model generated to represent a nested
    type to reconstruct the type annotation for the transfer model.
    """
    if isinstance(transfer_type, SimpleType):
        if transfer_type.transfer_model:
            return transfer_type.transfer_model.model
        return transfer_type.parsed_type.annotation

    if isinstance(transfer_type, CollectionType):
        return _create_transfer_model_collection_type(transfer_type)

    if isinstance(transfer_type, MappingType):
        return _create_transfer_model_mapping_type(transfer_type)

    if isinstance(transfer_type, TupleType):
        return _create_transfer_model_tuple_type(transfer_type)

    if isinstance(transfer_type, UnionType):
        return _create_transfer_model_union_type(transfer_type)

    raise RuntimeError(f"Unexpected transfer type: {type(transfer_type)}")


def _create_transfer_model_collection_type(transfer_type: CollectionType) -> Any:
    generic_collection_type = transfer_type.parsed_type.safe_generic_origin
    inner_type = create_transfer_model_type_annotation(transfer_type.inner_type)
    if transfer_type.parsed_type.origin is tuple:
        return generic_collection_type[inner_type, ...]
    return generic_collection_type[inner_type]


def _create_transfer_model_tuple_type(transfer_type: TupleType) -> Any:
    inner_types = tuple(create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.parsed_type.safe_generic_origin[inner_types]


def _create_transfer_model_union_type(transfer_type: UnionType) -> Any:
    inner_types = tuple(create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.parsed_type.safe_generic_origin[inner_types]


def _create_transfer_model_mapping_type(transfer_type: MappingType) -> Any:
    key_type = create_transfer_model_type_annotation(transfer_type.key_type)
    value_type = create_transfer_model_type_annotation(transfer_type.value_type)
    return transfer_type.parsed_type.safe_generic_origin[key_type, value_type]
