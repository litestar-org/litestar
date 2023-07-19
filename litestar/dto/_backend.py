"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
back again, to bytes.
"""
from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, AbstractSet, Any, Callable, Collection, Final, Mapping, Union, cast

from msgspec import UNSET, Struct, UnsetType, convert, defstruct, field
from typing_extensions import get_origin

from litestar.dto._types import (
    CollectionType,
    CompositeType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TransferDTOFieldDefinition,
    TransferType,
    TupleType,
    UnionType,
)
from litestar.dto.data_structures import DTOData, DTOFieldDefinition
from litestar.dto.field import Mark
from litestar.enums import RequestEncodingType
from litestar.exceptions import SerializationException
from litestar.serialization import decode_json, decode_msgpack
from litestar.types import Empty
from litestar.typing import FieldDefinition
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.dto import AbstractDTOFactory, RenameStrategy
    from litestar.dto._types import FieldDefinitionsType
    from litestar.dto.interface import ConnectionContext
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("DTOBackend",)


class DTOBackend:
    __slots__ = (
        "annotation",
        "dto_data_type",
        "field_definition",
        "dto_factory",
        "model_type",
        "parsed_field_definitions",
        "reverse_name_map",
        "transfer_model_type",
        "wrapper_attribute_name",
        "is_data_field",
    )

    def __init__(
        self,
        dto_factory: type[AbstractDTOFactory],
        field_definition: FieldDefinition,
        model_type: type[Any],
        wrapper_attribute_name: str | None,
        is_data_field: bool,
    ) -> None:
        """Create dto backend instance.

        Args:
            field_definition: Parsed type.
            dto_factory: The DTO factory class calling this backend.
            model_type: Model type.
            wrapper_attribute_name: If the data that DTO should operate upon is wrapped in a generic datastructure, this is the
                name of the attribute that the data is stored in.
            is_data_field: Whether or not the field is a subclass of DTOData.
        """
        self.dto_factory: Final[type[AbstractDTOFactory]] = dto_factory
        self.field_definition: Final[FieldDefinition] = field_definition
        self.is_data_field: Final[bool] = is_data_field
        self.model_type: Final[type[Any]] = model_type
        self.wrapper_attribute_name: Final[str | None] = wrapper_attribute_name

        self.parsed_field_definitions = self.parse_model(
            model_type=model_type, exclude=self.dto_factory.config.exclude, include=self.dto_factory.config.include
        )
        self.transfer_model_type = self.create_transfer_model_type(
            get_fully_qualified_class_name(model_type), self.parsed_field_definitions
        )
        self.dto_data_type: type[DTOData] | None = None

        if field_definition.is_subclass_of(DTOData):
            self.dto_data_type = field_definition.annotation
            annotation = self.field_definition.inner_types[0].annotation
        else:
            annotation = field_definition.annotation

        self.annotation = _maybe_wrap_in_generic_annotation(annotation, self.transfer_model_type)

    def parse_model(
        self, model_type: Any, exclude: AbstractSet[str], include: AbstractSet[str], nested_depth: int = 0
    ) -> FieldDefinitionsType:
        """Reduce :attr:`model_type` to :class:`FieldDefinitionsType`.

        .. important::
            Implementations must respect the :attr:`config` object. For example:
                - fields marked private must never be included in the field definitions.
                - if a ``purpose`` is declared, then read-only fields must be taken into account.
                - field renaming must be implemented.
                - additional fields must be included, subject to ``purpose``.
                - nested depth and nested recursion depth must be adhered to.

        Returns:
            Fields for data transfer.

            Key is the name of the new field, and value is a tuple of type and default value pairs.

            Add a new field called "new_field", that is a string, and required:
            {"new_field": (str, ...)}

            Add a new field called "new_field", that is a string, and not-required:
            {"new_field": (str, "default")}

            Add a new field called "new_field", that may be `None`:
            {"new_field": (str | None, None)}
        """
        defined_fields = []
        for field_definition in self.dto_factory.generate_field_definitions(model_type):
            if field_definition.dto_for and (
                field_definition.dto_for == "data"
                and not self.is_data_field
                or field_definition.dto_for == "return"
                and self.is_data_field
            ):
                continue

            if _should_mark_private(field_definition, self.dto_factory.config.underscore_fields_private):
                field_definition.dto_field.mark = Mark.PRIVATE

            try:
                transfer_type = self._create_transfer_type(
                    field_definition=field_definition,
                    exclude=exclude,
                    include=include,
                    field_name=field_definition.name,
                    unique_name=field_definition.unique_name(),
                    nested_depth=nested_depth,
                )
            except RecursionError:
                continue

            if rename := self.dto_factory.config.rename_fields.get(field_definition.name):
                serialization_name = rename
            elif self.dto_factory.config.rename_strategy:
                serialization_name = _rename_field(
                    name=field_definition.name, strategy=self.dto_factory.config.rename_strategy
                )
            else:
                serialization_name = field_definition.name

            transfer_field_definition = TransferDTOFieldDefinition.from_dto_field_definition(
                field_definition=field_definition,
                serialization_name=serialization_name,
                transfer_type=transfer_type,
                is_partial=self.dto_factory.config.partial,
                is_excluded=_should_exclude_field(
                    field_definition=field_definition,
                    exclude=exclude,
                    include=include,
                    is_data_field=self.is_data_field,
                ),
            )
            defined_fields.append(transfer_field_definition)
        return tuple(defined_fields)

    def create_transfer_model_type(self, unique_name: str, field_definitions: FieldDefinitionsType) -> type[Struct]:
        """Create a model for data transfer.

        Args:
            unique_name: name for the type that should be unique across all transfer types.
            field_definitions: field definitions for the container type.

        Returns:
            A ``BackendT`` class.
        """
        fqn_uid: str = self._gen_unique_name_id(unique_name)
        struct = _create_struct_for_field_definitions(fqn_uid, field_definitions)
        setattr(struct, "__schema_name__", unique_name)
        return struct

    def parse_raw(self, raw: bytes, connection_context: ConnectionContext) -> Struct | Collection[Struct]:
        """Parse raw bytes into transfer model type.

        Args:
            raw: bytes
            connection_context: Information about the active connection.

        Returns:
            The raw bytes parsed into transfer model type.
        """

        if connection_context.request_encoding_type not in [RequestEncodingType.JSON, RequestEncodingType.MESSAGEPACK]:
            raise SerializationException(
                f"Unsupported request encoding type: '{connection_context.request_encoding_type}'"
            )

        if connection_context.request_encoding_type == RequestEncodingType.JSON:
            result = decode_json(value=raw, target_type=self.annotation, type_decoders=connection_context.type_decoders)
        else:
            result = decode_msgpack(
                value=raw, target_type=self.annotation, type_decoders=connection_context.type_decoders
            )

        return cast("Struct | Collection[Struct]", result)

    def parse_builtins(self, builtins: Any, connection_context: ConnectionContext) -> Any:
        """Parse builtin types into transfer model type.

        Args:
            builtins: Builtin type.
            connection_context: Information about the active connection.

        Returns:
            The builtin type parsed into transfer model type.
        """
        return convert(
            obj=builtins,
            type=self.annotation,
            dec_hook=connection_context.default_deserializer,
            strict=False,
            str_keys=True,
        )

    def populate_data_from_builtins(self, builtins: Any, connection_context: ConnectionContext) -> Any:
        """Populate model instance from builtin types.

        Args:
            builtins: Builtin type.
            connection_context: Information about the active connection.

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        if self.dto_data_type:
            return self.dto_data_type(
                backend=self,
                data_as_builtins=_transfer_data(
                    destination_type=dict,
                    source_data=self.parse_builtins(builtins, connection_context),
                    field_definitions=self.parsed_field_definitions,
                    field_definition=self.field_definition,
                    is_data_field=self.is_data_field,
                ),
            )
        return self.transfer_data_from_builtins(self.parse_builtins(builtins, connection_context))

    def transfer_data_from_builtins(self, builtins: Any) -> Any:
        """Populate model instance from builtin types.

        Args:
            builtins: Builtin type.

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        return _transfer_data(
            destination_type=self.model_type,
            source_data=builtins,
            field_definitions=self.parsed_field_definitions,
            field_definition=self.field_definition,
            is_data_field=self.is_data_field,
        )

    def populate_data_from_raw(self, raw: bytes, connection_context: ConnectionContext) -> Any:
        """Parse raw bytes into instance of `model_type`.

        Args:
            raw: bytes
            connection_context: Information about the active connection.

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        if self.dto_data_type:
            return self.dto_data_type(
                backend=self,
                data_as_builtins=_transfer_data(
                    destination_type=dict,
                    source_data=self.parse_raw(raw, connection_context),
                    field_definitions=self.parsed_field_definitions,
                    field_definition=self.field_definition,
                    is_data_field=self.is_data_field,
                ),
            )
        return _transfer_data(
            destination_type=self.model_type,
            source_data=self.parse_raw(raw, connection_context),
            field_definitions=self.parsed_field_definitions,
            field_definition=self.field_definition,
            is_data_field=self.is_data_field,
        )

    def encode_data(self, data: Any) -> LitestarEncodableType:
        """Encode data into a ``LitestarEncodableType``.

        Args:
            data: Data to encode.

        Returns:
            Encoded data.
        """
        if self.wrapper_attribute_name:
            wrapped_transfer = _transfer_data(
                destination_type=self.transfer_model_type,
                source_data=getattr(data, self.wrapper_attribute_name),
                field_definitions=self.parsed_field_definitions,
                field_definition=self.field_definition,
                is_data_field=self.is_data_field,
            )
            setattr(
                data,
                self.wrapper_attribute_name,
                wrapped_transfer,
            )
            return cast("LitestarEncodableType", data)

        return cast(
            "LitestarEncodableType",
            _transfer_data(
                destination_type=self.transfer_model_type,
                source_data=data,
                field_definitions=self.parsed_field_definitions,
                field_definition=self.field_definition,
                is_data_field=self.is_data_field,
            ),
        )

    def create_openapi_schema(self, schema_creator: SchemaCreator) -> Reference | Schema:
        """Create an openAPI schema for the given DTO."""
        return schema_creator.for_field_definition(FieldDefinition.from_annotation(self.annotation))

    def _get_handler_for_field_definition(
        self, field_definition: FieldDefinition
    ) -> Callable[[FieldDefinition, AbstractSet[str], AbstractSet[str], str, int], CompositeType] | None:
        if field_definition.is_union:
            return self._create_union_type
        if field_definition.is_tuple:
            if len(field_definition.inner_types) == 2 and field_definition.inner_types[1].annotation is Ellipsis:
                return self._create_collection_type
            return self._create_tuple_type
        if field_definition.is_mapping:
            return self._create_mapping_type
        if field_definition.is_non_string_collection:
            return self._create_collection_type
        return None

    def _create_transfer_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        field_name: str,
        unique_name: str,
        nested_depth: int,
    ) -> CompositeType | SimpleType:
        exclude = _filter_nested_field(exclude, field_name)
        include = _filter_nested_field(include, field_name)

        if composite_type_handler := self._get_handler_for_field_definition(field_definition):
            return composite_type_handler(field_definition, exclude, include, unique_name, nested_depth)

        transfer_model: NestedFieldInfo | None = None
        if self.dto_factory.detect_nested_field(field_definition):
            if nested_depth == self.dto_factory.config.max_nested_depth:
                raise RecursionError

            nested_field_definitions = self.parse_model(
                model_type=field_definition.annotation, exclude=exclude, include=include, nested_depth=nested_depth + 1
            )

            transfer_model = NestedFieldInfo(
                model=self.create_transfer_model_type(unique_name, nested_field_definitions),
                field_definitions=nested_field_definitions,
            )

        return SimpleType(field_definition, nested_field_info=transfer_model)

    def _create_collection_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        unique_name: str,
        nested_depth: int,
    ) -> CollectionType:
        inner_types = field_definition.inner_types
        inner_type = self._create_transfer_type(
            field_definition=inner_types[0] if inner_types else FieldDefinition.from_annotation(Any),
            exclude=exclude,
            include=include,
            field_name="0",
            unique_name=f"{unique_name}_0",
            nested_depth=nested_depth,
        )
        return CollectionType(
            field_definition=field_definition, inner_type=inner_type, has_nested=inner_type.has_nested
        )

    def _create_mapping_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        unique_name: str,
        nested_depth: int,
    ) -> MappingType:
        inner_types = field_definition.inner_types
        key_type = self._create_transfer_type(
            field_definition=inner_types[0] if inner_types else FieldDefinition.from_annotation(Any),
            exclude=exclude,
            include=include,
            field_name="0",
            unique_name=f"{unique_name}_0",
            nested_depth=nested_depth,
        )
        value_type = self._create_transfer_type(
            field_definition=inner_types[1] if inner_types else FieldDefinition.from_annotation(Any),
            exclude=exclude,
            include=include,
            field_name="1",
            unique_name=f"{unique_name}_1",
            nested_depth=nested_depth,
        )
        return MappingType(
            field_definition=field_definition,
            key_type=key_type,
            value_type=value_type,
            has_nested=key_type.has_nested or value_type.has_nested,
        )

    def _create_tuple_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        unique_name: str,
        nested_depth: int,
    ) -> TupleType:
        inner_types = tuple(
            self._create_transfer_type(
                field_definition=inner_type,
                exclude=exclude,
                include=include,
                field_name=str(i),
                unique_name=f"{unique_name}_{i}",
                nested_depth=nested_depth,
            )
            for i, inner_type in enumerate(field_definition.inner_types)
        )
        return TupleType(
            field_definition=field_definition,
            inner_types=inner_types,
            has_nested=any(t.has_nested for t in inner_types),
        )

    def _create_union_type(
        self,
        field_definition: FieldDefinition,
        exclude: AbstractSet[str],
        include: AbstractSet[str],
        unique_name: str,
        nested_depth: int,
    ) -> UnionType:
        inner_types = tuple(
            self._create_transfer_type(
                field_definition=inner_type,
                exclude=exclude,
                include=include,
                field_name=str(i),
                unique_name=f"{unique_name}_{i}",
                nested_depth=nested_depth,
            )
            for i, inner_type in enumerate(field_definition.inner_types)
        )
        return UnionType(
            field_definition=field_definition,
            inner_types=inner_types,
            has_nested=any(t.has_nested for t in inner_types),
        )

    @staticmethod
    def _gen_unique_name_id(unique_name: str) -> str:
        # Generate a unique ID
        # Convert the ID to a short alphanumeric string
        return f"{unique_name}-{secrets.token_hex(8)}"


def _camelize(value: str, capitalize_first_letter: bool) -> str:
    return "".join(
        word if index == 0 and not capitalize_first_letter else word.capitalize()
        for index, word in enumerate(value.split("_"))
    )


def _rename_field(name: str, strategy: RenameStrategy) -> str:
    if callable(strategy):
        return strategy(name)

    if strategy == "camel":
        return _camelize(value=name, capitalize_first_letter=False)

    if strategy == "pascal":
        return _camelize(value=name, capitalize_first_letter=True)

    if strategy == "lower":
        return name.lower()

    return name.upper()


def _filter_nested_field(field_name_set: AbstractSet[str], field_name: str) -> AbstractSet[str]:
    """Filter a nested field name."""
    return {split[1] for s in field_name_set if (split := s.split(".", 1))[0] == field_name and len(split) > 1}


def _transfer_data(
    destination_type: type[Any],
    source_data: Any | Collection[Any],
    field_definitions: FieldDefinitionsType,
    field_definition: FieldDefinition,
    is_data_field: bool,
) -> Any:
    """Create instance or iterable of instances of ``destination_type``.

    Args:
        destination_type: the model type received by the DTO on type narrowing.
        source_data: data that has been parsed and validated via the backend.
        field_definitions: model field definitions.
        field_definition: the parsed type that represents the handler annotation for which the DTO is being applied.
        is_data_field: whether the DTO is being applied to a ``data`` field.

    Returns:
        Data parsed into ``destination_type``.
    """
    if field_definition.is_non_string_collection and not field_definition.is_mapping:
        return field_definition.instantiable_origin(
            _transfer_data(
                destination_type=destination_type,
                source_data=item,
                field_definitions=field_definitions,
                field_definition=field_definition.inner_types[0],
                is_data_field=is_data_field,
            )
            for item in source_data
        )

    return _transfer_instance_data(
        destination_type=destination_type,
        source_instance=source_data,
        field_definitions=field_definitions,
        is_data_field=is_data_field,
    )


def _transfer_instance_data(
    destination_type: type[Any], source_instance: Any, field_definitions: FieldDefinitionsType, is_data_field: bool
) -> Any:
    """Create instance of ``destination_type`` with data from ``source_instance``.

    Args:
        destination_type: the model type received by the DTO on type narrowing.
        source_instance: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.
        is_data_field: whether the given field is a 'data' kwarg field.

    Returns:
        Data parsed into ``model_type``.
    """
    unstructured_data = {}
    source_is_mapping = isinstance(source_instance, Mapping)

    def filter_missing(value: Any) -> bool:
        return value is UNSET

    for field_definition in field_definitions:
        source_name = field_definition.serialization_name if is_data_field else field_definition.name
        source_has_value = (
            source_name in source_instance if source_is_mapping else hasattr(source_instance, source_name)
        )

        if (is_data_field and not source_has_value) or (not is_data_field and field_definition.is_excluded):
            continue

        transfer_type = field_definition.transfer_type
        destination_name = field_definition.name if is_data_field else field_definition.serialization_name
        source_value = source_instance[source_name] if source_is_mapping else getattr(source_instance, source_name)

        if field_definition.is_partial and is_data_field and filter_missing(source_value):
            continue

        unstructured_data[destination_name] = _transfer_type_data(
            source_value=source_value,
            transfer_type=transfer_type,
            nested_as_dict=destination_type is dict,
            is_data_field=is_data_field,
        )
    return destination_type(**unstructured_data)


def _transfer_type_data(
    source_value: Any, transfer_type: TransferType, nested_as_dict: bool, is_data_field: bool
) -> Any:
    if isinstance(transfer_type, SimpleType) and transfer_type.nested_field_info:
        if nested_as_dict:
            destination_type: Any = dict
        elif is_data_field:
            destination_type = transfer_type.field_definition.annotation
        else:
            destination_type = transfer_type.nested_field_info.model

        return _transfer_instance_data(
            destination_type=destination_type,
            source_instance=source_value,
            field_definitions=transfer_type.nested_field_info.field_definitions,
            is_data_field=is_data_field,
        )

    if isinstance(transfer_type, UnionType) and transfer_type.has_nested:
        return _transfer_nested_union_type_data(
            transfer_type=transfer_type, source_value=source_value, is_data_field=is_data_field
        )

    if isinstance(transfer_type, CollectionType):
        if transfer_type.has_nested:
            return transfer_type.field_definition.instantiable_origin(
                _transfer_type_data(
                    source_value=item,
                    transfer_type=transfer_type.inner_type,
                    nested_as_dict=False,
                    is_data_field=is_data_field,
                )
                for item in source_value
            )

        return transfer_type.field_definition.instantiable_origin(source_value)
    return source_value


def _transfer_nested_union_type_data(transfer_type: UnionType, source_value: Any, is_data_field: bool) -> Any:
    for inner_type in transfer_type.inner_types:
        if isinstance(inner_type, CompositeType):
            raise RuntimeError("Composite inner types not (yet) supported for nested unions.")

        if inner_type.nested_field_info and isinstance(
            source_value,
            inner_type.nested_field_info.model if is_data_field else inner_type.field_definition.annotation,
        ):
            return _transfer_instance_data(
                destination_type=inner_type.field_definition.annotation
                if is_data_field
                else inner_type.nested_field_info.model,
                source_instance=source_value,
                field_definitions=inner_type.nested_field_info.field_definitions,
                is_data_field=is_data_field,
            )
    return source_value


def _create_msgspec_field(field_definition: TransferDTOFieldDefinition) -> Any:
    kwargs: dict[str, Any] = {}
    if field_definition.is_partial:
        kwargs["default"] = UNSET

    elif field_definition.default is not Empty:
        kwargs["default"] = field_definition.default

    elif field_definition.default_factory is not None:
        kwargs["default_factory"] = field_definition.default_factory

    return field(**kwargs)


def _create_struct_for_field_definitions(model_name: str, field_definitions: FieldDefinitionsType) -> type[Struct]:
    struct_fields: list[tuple[str, type] | tuple[str, type, type]] = []
    for field_def in field_definitions:
        if field_def.is_excluded:
            continue

        field_name = field_def.serialization_name or field_def.name

        field_type = _create_transfer_model_type_annotation(field_def.transfer_type)
        if field_def.is_partial:
            field_type = Union[field_type, UnsetType]

        struct_fields.append((field_name, field_type, _create_msgspec_field(field_def)))
    return defstruct(model_name, struct_fields, frozen=True, kw_only=True)


def _maybe_wrap_in_generic_annotation(annotation: Any, model: Any) -> Any:
    """A helper to re-build a generic outer type with new inner type.

    Args:
        annotation: The original annotation on the handler signature
        model: The data container type

    Returns:
        Annotation with new inner type if applicable.
    """
    return origin[model] if (origin := get_origin(annotation)) else model


def _should_mark_private(field_definition: DTOFieldDefinition, underscore_fields_private: bool) -> bool:
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


def _should_exclude_field(
    field_definition: DTOFieldDefinition, exclude: AbstractSet[str], include: AbstractSet[str], is_data_field: bool
) -> bool:
    """Returns ``True`` where a field should be excluded from data transfer.

    Args:
        field_definition: defined DTO field
        exclude: names of fields to exclude
        include: names of fields to exclude
        is_data_field: whether the field is a data field

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
    if is_data_field and field_definition.dto_field.mark is Mark.READ_ONLY:
        return True
    return field_definition.name != "return" and field_definition.dto_field.mark is Mark.WRITE_ONLY


def _create_transfer_model_type_annotation(transfer_type: TransferType) -> Any:
    """Create a type annotation for a transfer model.

    Uses the parsed type that originates from the data model and the transfer model generated to represent a nested
    type to reconstruct the type annotation for the transfer model.
    """
    if isinstance(transfer_type, SimpleType):
        if transfer_type.nested_field_info:
            return transfer_type.nested_field_info.model
        return transfer_type.field_definition.annotation

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
    generic_collection_type = transfer_type.field_definition.safe_generic_origin
    inner_type = _create_transfer_model_type_annotation(transfer_type.inner_type)
    if transfer_type.field_definition.origin is tuple:
        return generic_collection_type[inner_type, ...]
    return generic_collection_type[inner_type]


def _create_transfer_model_tuple_type(transfer_type: TupleType) -> Any:
    inner_types = tuple(_create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.field_definition.safe_generic_origin[inner_types]


def _create_transfer_model_union_type(transfer_type: UnionType) -> Any:
    inner_types = tuple(_create_transfer_model_type_annotation(t) for t in transfer_type.inner_types)
    return transfer_type.field_definition.safe_generic_origin[inner_types]


def _create_transfer_model_mapping_type(transfer_type: MappingType) -> Any:
    key_type = _create_transfer_model_type_annotation(transfer_type.key_type)
    value_type = _create_transfer_model_type_annotation(transfer_type.value_type)
    return transfer_type.field_definition.safe_generic_origin[key_type, value_type]
