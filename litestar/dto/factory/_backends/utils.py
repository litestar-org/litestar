from __future__ import annotations

from collections.abc import Collection as CollectionsCollection
from typing import TYPE_CHECKING, TypeVar, cast

from typing_extensions import get_origin

from litestar.dto.factory import Mark
from litestar.types.builtin_types import NoneType
from litestar.utils.signature import ParsedType

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
    "get_model_type",
    "should_exclude_field",
    "_build_data_from_transfer_data",
    "_build_transfer_instance_from_model",
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


def get_model_type(annotation: type) -> Any:
    """Get model type represented by the DTO.

    If ``annotation`` is a collection, then the inner type is returned.

    Args:
        annotation: any type.

    Returns:
        The model type that is represented by the DTO.
    """
    parsed_type = ParsedType(annotation)
    if parsed_type.is_collection:
        return parsed_type.inner_types[0].annotation
    if parsed_type.is_optional:
        return next(t for t in parsed_type.inner_types if t.annotation is not NoneType).annotation
    return parsed_type.annotation


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


def _build_model_from_transfer_instance(
    model_type: type[T], data: Struct, field_definitions: FieldDefinitionsType
) -> T:
    """Create instance of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    unstructured_data = {}
    for field_definition in field_definitions.values():
        transfer_type = field_definition.transfer_type
        transfer_model_name = field_definition.serialization_name or field_definition.name
        v = getattr(data, transfer_model_name)
        if isinstance(transfer_type, SimpleType) and transfer_type.transfer_model:
            unstructured_data[field_definition.name] = _build_model_from_transfer_instance(
                transfer_type.parsed_type.annotation, v, transfer_type.transfer_model.field_definitions
            )
        elif isinstance(transfer_type, UnionType) and transfer_type.has_nested:
            for inner_type in transfer_type.inner_types:
                if (
                    isinstance(inner_type, SimpleType)
                    and inner_type.transfer_model
                    and isinstance(v, inner_type.transfer_model.model)
                ):
                    unstructured_data[field_definition.name] = _build_model_from_transfer_instance(
                        inner_type.parsed_type.annotation, v, inner_type.transfer_model.field_definitions
                    )
        elif isinstance(transfer_type, CollectionType) and transfer_type.has_nested:
            if field_definition.parsed_type.origin is None:  # pragma: no cover
                raise RuntimeError("Unexpected origin value for collection type.")

            if not isinstance(transfer_type.inner_type, SimpleType):
                raise RuntimeError("Compound inner types not yet supported")

            if transfer_type.inner_type.transfer_model is None:
                raise RuntimeError("Inner type expected to have transfer model")

            unstructured_data[field_definition.name] = field_definition.parsed_type.origin(
                _build_model_from_transfer_instance(
                    transfer_type.inner_type.parsed_type.annotation,
                    item,
                    transfer_type.inner_type.transfer_model.field_definitions,
                )
                for item in v
            )
        else:
            unstructured_data[field_definition.name] = v

    return model_type(**unstructured_data)


def _build_data_from_transfer_data(
    model_type: type[T],
    data: Any | Collection[Any],
    field_definitions: FieldDefinitionsType,
) -> T | Collection[T]:
    """Create instance or iterable of instances of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    if isinstance(data, CollectionsCollection):
        return type(data)(
            _build_data_from_transfer_data(model_type, item, field_definitions)  # type:ignore[call-arg]
            for item in data
        )
    return _build_model_from_transfer_instance(model_type, data, field_definitions)


def _build_transfer_instance_from_model(
    model: Any, transfer_annotation: type[Any], field_definitions: FieldDefinitionsType
) -> Any:
    """Convert ``model`` to instance of ``struct_type``

    It is expected that attributes of ``struct_type`` are a subset of the attributes of ``model``.

    Args:
        model: a model instance
        transfer_annotation: the transfer type built for the data model
        field_definitions: model field definitions.

    Returns:
        Instance of ``struct_type``.
    """
    data = {}
    for field_definition in field_definitions.values():
        transfer_type = field_definition.transfer_type
        key = field_definition.serialization_name or field_definition.name
        model_val = getattr(model, field_definition.name)
        if isinstance(transfer_type, SimpleType) and transfer_type.transfer_model:
            data[key] = _build_transfer_instance_from_model(
                model_val, transfer_type.transfer_model.model, transfer_type.transfer_model.field_definitions
            )
        elif isinstance(transfer_type, UnionType) and transfer_type.has_nested:
            for inner_type in transfer_type.inner_types:
                if (
                    isinstance(inner_type, SimpleType)
                    and inner_type.transfer_model
                    and isinstance(model_val, inner_type.parsed_type.annotation)
                ):
                    data[key] = _build_transfer_instance_from_model(
                        model_val, inner_type.transfer_model.model, inner_type.transfer_model.field_definitions
                    )
        elif isinstance(transfer_type, CollectionType) and transfer_type.has_nested:
            if field_definition.parsed_type.origin is None:  # pragma: no cover
                raise RuntimeError("Unexpected origin value for collection type.")

            if not isinstance(transfer_type.inner_type, SimpleType):
                raise RuntimeError("Composite inner types not yet supported")

            if not transfer_type.inner_type.transfer_model:
                raise RuntimeError("Expected transfer model for inner type")

            data[key] = field_definition.parsed_type.origin(
                _build_transfer_instance_from_model(
                    m,
                    transfer_type.inner_type.transfer_model.model,
                    transfer_type.inner_type.transfer_model.field_definitions,
                )
                for m in model_val
            )
        else:
            data[key] = model_val
    return transfer_annotation(**data)


def create_transfer_model_type_annotation(transfer_type: TransferType) -> Any:
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
