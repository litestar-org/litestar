from __future__ import annotations

from typing import TYPE_CHECKING, Collection, TypeVar, cast
from typing import Collection as CollectionsCollection

from typing_extensions import get_origin

from litestar.dto.factory import Mark
from litestar.types.builtin_types import NoneType
from litestar.utils.signature import ParsedType

from .types import NestedFieldDefinition

if TYPE_CHECKING:
    from typing import AbstractSet, Any, Iterable

    from msgspec import Struct

    from litestar.dto.factory.types import FieldDefinition, RenameStrategy
    from litestar.dto.types import ForType

    from .types import FieldDefinitionsType

__all__ = (
    "RenameStrategies",
    "build_annotation_for_backend",
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
        transfer_model_name = field_definition.serialization_name or field_definition.name
        v = getattr(data, transfer_model_name)
        if isinstance(field_definition, NestedFieldDefinition) and field_definition.parsed_type.is_collection:
            if field_definition.parsed_type.origin is None:  # pragma: no cover
                raise RuntimeError("Unexpected origin value for collection type.")
            unstructured_data[field_definition.name] = field_definition.parsed_type.origin(
                _build_model_from_transfer_instance(
                    field_definition.nested_type, item, field_definition.nested_field_definitions
                )
                for item in v
            )
        elif isinstance(field_definition, NestedFieldDefinition) and v is not None:
            unstructured_data[field_definition.name] = _build_model_from_transfer_instance(
                field_definition.nested_type, v, field_definition.nested_field_definitions
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
    model: Any, transfer_type: type[Any], field_definitions: FieldDefinitionsType
) -> Any:
    """Convert ``model`` to instance of ``struct_type``

    It is expected that attributes of ``struct_type`` are a subset of the attributes of ``model``.

    Args:
        model: a model instance
        transfer_type: the transfer type built for the data model
        field_definitions: model field definitions.

    Returns:
        Instance of ``struct_type``.
    """
    data = {}
    for field_definition in field_definitions.values():
        key = field_definition.serialization_name or field_definition.name
        model_val = getattr(model, field_definition.name)
        if isinstance(field_definition, NestedFieldDefinition) and field_definition.parsed_type.is_collection:
            data[key] = _handle_collection_type(field_definition, model_val)
        elif isinstance(field_definition, NestedFieldDefinition) and model_val is not None:
            data[key] = _build_transfer_instance_from_model(
                model_val, field_definition.transfer_model, field_definition.nested_field_definitions
            )
        else:
            data[key] = model_val
    return transfer_type(**data)


def _handle_collection_type(field_definition: NestedFieldDefinition, model_val: Any) -> Any:
    """Handle collection type.

    Args:
        field_definition: Field definition.
        model_val: Model value.

    Returns:
        Model value.
    """
    return field_definition.parsed_type.origin(
        _build_transfer_instance_from_model(
            m, field_definition.transfer_model, field_definition.nested_field_definitions
        )
        for m in model_val
    )
