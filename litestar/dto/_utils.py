from __future__ import annotations

import typing
from inspect import getmodule
from typing import TYPE_CHECKING, Collection, Mapping, TypeVar, Union, cast

from msgspec import UNSET, Struct, UnsetType, defstruct, field
from typing_extensions import get_origin, get_type_hints

from litestar.dto._types import (
    CollectionType,
    CompositeType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TransferType,
    TupleType,
    UnionType,
)
from litestar.dto.config import DTOConfig
from litestar.dto.data_structures import DTOData
from litestar.dto.field import Mark
from litestar.dto.types import ForType, RenameStrategy
from litestar.enums import RequestEncodingType
from litestar.types import Empty
from litestar.types.builtin_types import NoneType
from litestar.types.composite_types import TypeEncodersMap
from litestar.types.protocols import InstantiableCollection
from litestar.typing import FieldDefinition
from litestar.utils import find_index

if TYPE_CHECKING:
    from typing import AbstractSet, Any, Iterable

    from litestar.dto._types import FieldDefinitionsType, TransferDTOFieldDefinition
    from litestar.dto.data_structures import DTOFieldDefinition

__all__ = (
    "RenameStrategies",
    "build_annotation_for_backend",
    "create_msgspec_field",
    "create_struct_for_field_definitions",
    "create_transfer_model_type_annotation",
    "get_dto_config_from_annotated_type",
    "get_model_type_hints",
    "resolve_generic_wrapper_type",
    "resolve_model_type",
    "should_exclude_field",
    "should_ignore_field",
    "should_mark_private",
    "transfer_data",
    "transfer_nested_union_type_data",
)

T = TypeVar("T")
StructT = TypeVar("StructT", bound=Struct)


def get_model_type_hints(model_type: type[Any], namespace: dict[str, Any] | None = None) -> dict[str, FieldDefinition]:
    """Retrieve type annotations for ``model_type``.

    Args:
        model_type: Any type-annotated class.
        namespace: Optional namespace to use for resolving type hints.

    Returns:
        Parsed type hints for ``model_type`` resolved within the scope of its module.
    """
    namespace = namespace or {}
    namespace.update(vars(typing))
    namespace.update(
        {
            "TypeEncodersMap": TypeEncodersMap,
            "ForType": ForType,
            "DTOConfig": DTOConfig,
            "RenameStrategy": RenameStrategy,
            "RequestEncodingType": RequestEncodingType,
        }
    )

    if model_module := getmodule(model_type):
        namespace.update(vars(model_module))

    return {
        k: FieldDefinition.from_kwarg(annotation=v, name=k)
        for k, v in get_type_hints(model_type, localns=namespace, include_extras=True).items()
    }


def get_dto_config_from_annotated_type(field_definition: FieldDefinition) -> DTOConfig | None:
    """Extract data type and config instances from ``Annotated`` annotation.

    Args:
        field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.

    Returns:
        The type and config object extracted from the annotation.
    """
    if configs := [item for item in field_definition.metadata if isinstance(item, DTOConfig)]:
        return configs[0]
    return None


def resolve_model_type(field_definition: FieldDefinition) -> FieldDefinition:
    """Resolve the data model type from a parsed type.

    Args:
        field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.

    Returns:
        A :class:`FieldDefinition <.typing.FieldDefinition>` that represents the data model type.
    """
    if field_definition.is_optional:
        return resolve_model_type(next(t for t in field_definition.inner_types if not t.is_subclass_of(NoneType)))

    if field_definition.is_subclass_of(DTOData):
        return resolve_model_type(field_definition.inner_types[0])

    if field_definition.is_collection:
        if field_definition.is_mapping:
            return resolve_model_type(field_definition.inner_types[1])

        if field_definition.is_tuple:
            if any(t is Ellipsis for t in field_definition.args):
                return resolve_model_type(field_definition.inner_types[0])
        elif field_definition.is_non_string_collection:
            return resolve_model_type(field_definition.inner_types[0])

    return field_definition


def resolve_generic_wrapper_type(
    field_definition: FieldDefinition, dto_specialized_type: type[Any]
) -> tuple[FieldDefinition, FieldDefinition, str] | None:
    """Handle where DTO supported data is wrapped in a generic container type.

    Args:
        field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.
        dto_specialized_type: The type used to specialize the DTO.

    Returns:
        The data model type.
    """
    if (origin := field_definition.origin) and (parameters := getattr(origin, "__parameters__", None)):
        param_index = find_index(
            field_definition.inner_types, lambda x: resolve_model_type(x).is_subclass_of(dto_specialized_type)
        )

        if param_index == -1:
            return None

        inner_type = field_definition.inner_types[param_index]
        model_type = resolve_model_type(inner_type)
        type_var = parameters[param_index]

        for attr, attr_type in get_model_type_hints(origin).items():
            if attr_type.annotation is type_var or any(t.annotation is type_var for t in attr_type.inner_types):
                if attr_type.is_non_string_collection:
                    # the inner type of the collection type is the type var, so we need to specialize the
                    # collection type with the DTO supported type.
                    specialized_annotation = attr_type.safe_generic_origin[model_type.annotation]
                    return model_type, FieldDefinition.from_annotation(specialized_annotation), attr
                return model_type, inner_type, attr

    return None


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


def should_mark_private(field_definition: DTOFieldDefinition, underscore_fields_private: bool) -> bool:
    """Returns ``True`` where a field should be marked as private.

    Fields should be marked as private when:
    - the ``underscore_fields_private`` flag is set.
    - the field is not already marked.
    - the field name is prefixed with an underscore

    Args:
        field_definition: defined DTO field
        underscore_fields_private: whether fields prefixed with an underscore should be marked as private.
    """
    return bool(
        underscore_fields_private and field_definition.dto_field.mark is None and field_definition.name.startswith("_")
    )


def should_exclude_field(
    field_definition: DTOFieldDefinition, exclude: AbstractSet[str], include: AbstractSet[str], dto_for: ForType
) -> bool:
    """Returns ``True`` where a field should be excluded from data transfer.

    Args:
        field_definition: defined DTO field
        exclude: names of fields to exclude
        include: names of fields to exclude
        dto_for: indicates whether the DTO is for the request body or response.

    Returns:
        ``True`` if the field should not be included in any data transfer.
    """
    field_name = field_definition.name
    if field_name in exclude:
        return True
    if include and field_name not in include and not (any(f.startswith(f"{field_name}.") for f in include)):
        return True
    if field_definition.dto_field.mark is Mark.PRIVATE:
        return True
    if dto_for == "data" and field_definition.dto_field.mark is Mark.READ_ONLY:
        return True
    return dto_for == "return" and field_definition.dto_field.mark is Mark.WRITE_ONLY


def should_ignore_field(field_definition: DTOFieldDefinition, dto_for: ForType) -> bool:
    """Returns ``True`` where a field should be ignored.

    An ignored field is different to an excluded one in that we do not produce a
    ``TransferFieldDefinition`` for it at all.

    This allows ``AbstractDTOFactory`` concrete types to generate multiple field definitions
    for the same field name, each for a different transfer direction.

    One example of this is the :class:`sqlalchemy.ext.hybrid.hybrid_property` which, might have
    a different type accepted by its setter method, than is returned by its getter method.
    """
    return field_definition.dto_for is not None and field_definition.dto_for != dto_for


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


def transfer_data(
    destination_type: type[T],
    source_data: Any | Collection[Any],
    field_definitions: FieldDefinitionsType,
    dto_for: ForType,
    field_definition: FieldDefinition,
) -> T | InstantiableCollection[T]:
    """Create instance or iterable of instances of ``destination_type``.

    Args:
        destination_type: the model type received by the DTO on type narrowing.
        source_data: data that has been parsed and validated via the backend.
        field_definitions: model field definitions.
        dto_for: indicates whether the DTO is for the request body or response.
        field_definition: the parsed type that represents the handler annotation for which the DTO is being applied.

    Returns:
        Data parsed into ``destination_type``.
    """
    if field_definition.is_non_string_collection and not field_definition.is_mapping:
        origin = field_definition.instantiable_origin
        if not issubclass(origin, InstantiableCollection):  # pragma: no cover
            raise RuntimeError(
                f"Unexpected origin type '{field_definition.instantiable_origin}', expected collection type"
            )

        return origin(  # type:ignore[no-any-return]
            transfer_data(destination_type, item, field_definitions, dto_for, field_definition.inner_types[0])
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

    def has(source: Any, key: str) -> bool:
        return key in source if source_is_mapping else hasattr(source, key)

    def get(source: Any, key: str) -> Any:
        return source[key] if source_is_mapping else getattr(source, key)

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


def should_skip_transfer(
    dto_for: ForType,
    field_definition: TransferDTOFieldDefinition,
    source_has_value: bool,
) -> bool:
    """Returns ``True`` where a field should be excluded from data transfer.

    We should skip transfer when:
    - the field is excluded and the DTO is for the return data.
    - the DTO is for request data, and the field is not in the source instance.

    Args:
        dto_for: indicates whether the DTO is for the request body or response.
        field_definition: model field definition.
        source_has_value: indicates whether the source instance has a value for the field.
    """
    return (dto_for == "return" and field_definition.is_excluded) or (dto_for == "data" and not source_has_value)


def transfer_type_data(
    source_value: Any, transfer_type: TransferType, dto_for: ForType, nested_as_dict: bool = False
) -> Any:
    if isinstance(transfer_type, SimpleType) and transfer_type.nested_field_info:
        if nested_as_dict:
            dest_type = dict
        else:
            dest_type = (
                transfer_type.field_definition.annotation
                if dto_for == "data"
                else transfer_type.nested_field_info.model
            )

        return transfer_nested_simple_type_data(dest_type, transfer_type.nested_field_info, dto_for, source_value)
    if isinstance(transfer_type, UnionType) and transfer_type.has_nested:
        return transfer_nested_union_type_data(transfer_type, dto_for, source_value)
    if isinstance(transfer_type, CollectionType):
        if transfer_type.has_nested:
            return transfer_nested_collection_type_data(
                transfer_type.field_definition.instantiable_origin, transfer_type, dto_for, source_value
            )
        return transfer_type.field_definition.instantiable_origin(source_value)
    return source_value


def transfer_nested_collection_type_data(
    origin_type: type[Any], transfer_type: CollectionType, dto_for: ForType, source_value: Any
) -> Any:
    return origin_type(transfer_type_data(item, transfer_type.inner_type, dto_for) for item in source_value)


def transfer_nested_simple_type_data(
    destination_type: type[T],  # pyright: ignore
    nested_field_info: NestedFieldInfo,
    dto_for: ForType,
    source_value: Any,
) -> Any:
    return transfer_instance_data(destination_type, source_value, nested_field_info.field_definitions, dto_for)


def transfer_nested_union_type_data(transfer_type: UnionType, dto_for: ForType, source_value: Any) -> Any:
    for inner_type in transfer_type.inner_types:
        if isinstance(inner_type, CompositeType):
            raise RuntimeError("Composite inner types not (yet) supported for nested unions.")

        if inner_type.nested_field_info and isinstance(
            source_value,
            inner_type.nested_field_info.model if dto_for == "data" else inner_type.field_definition.annotation,
        ):
            return transfer_instance_data(
                inner_type.field_definition.annotation if dto_for == "data" else inner_type.nested_field_info.model,
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
        return transfer_type.field_definition.annotation

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
    generic_collection_type = transfer_type.field_definition.safe_generic_origin
    inner_type = create_transfer_model_type_annotation(transfer_type.inner_type)
    if transfer_type.field_definition.origin is tuple:
        return generic_collection_type[inner_type, ...]
    return generic_collection_type[inner_type]


def create_transfer_model_tuple_type(transfer_type: TupleType) -> Any:
    inner_types = tuple(create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.field_definition.safe_generic_origin[inner_types]


def create_transfer_model_union_type(transfer_type: UnionType) -> Any:
    inner_types = tuple(create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.field_definition.safe_generic_origin[inner_types]


def create_transfer_model_mapping_type(transfer_type: MappingType) -> Any:
    key_type = create_transfer_model_type_annotation(transfer_type.key_type)
    value_type = create_transfer_model_type_annotation(transfer_type.value_type)
    return transfer_type.field_definition.safe_generic_origin[key_type, value_type]


def create_msgspec_field(field_definition: TransferDTOFieldDefinition) -> Any:
    kwargs: dict[str, Any] = {}
    if field_definition.is_partial:
        kwargs["default"] = UNSET

    elif field_definition.default is not Empty:
        kwargs["default"] = field_definition.default

    elif field_definition.default_factory is not None:
        kwargs["default_factory"] = field_definition.default_factory

    return field(**kwargs)


def create_struct_for_field_definitions(model_name: str, field_definitions: FieldDefinitionsType) -> type[Struct]:
    struct_fields: list[tuple[str, type] | tuple[str, type, type]] = []
    for field_def in field_definitions:
        if field_def.is_excluded:
            continue

        field_name = field_def.serialization_name or field_def.name

        field_type = create_transfer_model_type_annotation(field_def.transfer_type)
        if field_def.is_partial:
            field_type = Union[field_type, UnsetType]

        struct_fields.append((field_name, field_type, create_msgspec_field(field_def)))
    return defstruct(model_name, struct_fields, frozen=True, kw_only=True)
