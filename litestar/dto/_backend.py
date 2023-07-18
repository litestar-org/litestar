"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
back again, to bytes.
"""
from __future__ import annotations

import secrets
from typing import TYPE_CHECKING, Any, Final, cast

from msgspec import Struct, convert

from litestar.dto._types import (
    CollectionType,
    CompositeType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TransferDTOFieldDefinition,
    TupleType,
    UnionType,
)
from litestar.dto._utils import (
    RenameStrategies,
    build_annotation_for_backend,
    create_struct_for_field_definitions,
    should_exclude_field,
    should_ignore_field,
    should_mark_private,
    transfer_data,
)
from litestar.dto.data_structures import DTOData
from litestar.dto.field import Mark
from litestar.enums import RequestEncodingType
from litestar.exceptions import SerializationException
from litestar.serialization import decode_json, decode_msgpack
from litestar.typing import FieldDefinition
from litestar.utils.helpers import get_fully_qualified_class_name

if TYPE_CHECKING:
    from typing import AbstractSet, Callable, Collection, Generator

    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.dto import DTOConfig
    from litestar.dto._types import FieldDefinitionsType
    from litestar.dto.data_structures import DTOFieldDefinition
    from litestar.dto.interface import ConnectionContext
    from litestar.dto.types import ForType
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("DTOBackend", "BackendContext")


class BackendContext:
    """Context required by DTO backends to perform their work."""

    __slots__ = (
        "config",
        "dto_for",
        "field_definition_generator",
        "is_nested_field_predicate",
        "model_type",
        "field_definition",
        "wrapper_attribute_name",
    )

    def __init__(
        self,
        dto_config: DTOConfig,
        dto_for: ForType,
        field_definition: FieldDefinition,
        field_definition_generator: Callable[[Any], Generator[DTOFieldDefinition, None, None]],
        is_nested_field_predicate: Callable[[FieldDefinition], bool],
        model_type: type[Any],
        wrapper_attribute_name: str | None,
    ) -> None:
        """Create a backend context.

        Args:
            dto_config: DTO config.
            dto_for: "data" or "return"
            field_definition: Parsed type.
            field_definition_generator: Generator that produces
                :class:`FieldDefinition <.dto.factory.types.FieldDefinition>` instances given ``model_type``.
            is_nested_field_predicate: Function that detects if a field is nested.
            model_type: Model type.
            wrapper_attribute_name: If the data that DTO should operate upon is wrapped in a generic datastructure, this is the
                name of the attribute that the data is stored in.
        """
        self.config: Final[DTOConfig] = dto_config
        self.dto_for: Final[ForType] = dto_for
        self.field_definition: Final[FieldDefinition] = field_definition
        self.field_definition_generator: Final[
            Callable[[Any], Generator[DTOFieldDefinition, None, None]]
        ] = field_definition_generator
        self.is_nested_field_predicate: Final[Callable[[FieldDefinition], bool]] = is_nested_field_predicate
        self.model_type: Final[type[Any]] = model_type
        self.wrapper_attribute_name = wrapper_attribute_name


class NestedDepthExceededError(Exception):
    """Raised when a nested type exceeds the maximum allowed depth.

    Not an exception that is intended to be raised into userland, rather a signal to the process that is iterating over
    the field definitions that the current field should be skipped.
    """


class DTOBackend:
    __slots__ = (
        "annotation",
        "context",
        "dto_data_type",
        "parsed_field_definitions",
        "reverse_name_map",
        "transfer_model_type",
    )

    def __init__(self, context: BackendContext) -> None:
        """Create dto backend instance.

        Args:
            context: context of the type represented by this backend.
        """
        self.context = context
        self.parsed_field_definitions = self.parse_model(
            model_type=context.model_type, exclude=context.config.exclude, include=context.config.include
        )
        self.transfer_model_type = self.create_transfer_model_type(
            get_fully_qualified_class_name(context.model_type), self.parsed_field_definitions
        )
        self.dto_data_type: type[DTOData] | None = None
        if context.field_definition.is_subclass_of(DTOData):
            self.dto_data_type = context.field_definition.annotation
            annotation = self.context.field_definition.inner_types[0].annotation
        else:
            annotation = context.field_definition.annotation
        self.annotation = build_annotation_for_backend(annotation, self.transfer_model_type)

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
        for field_definition in self.context.field_definition_generator(model_type):
            if should_ignore_field(field_definition, self.context.dto_for):
                continue

            if should_mark_private(field_definition, self.context.config.underscore_fields_private):
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
            except NestedDepthExceededError:
                continue

            if rename := self.context.config.rename_fields.get(field_definition.name):
                serialization_name = rename
            elif self.context.config.rename_strategy:
                serialization_name = RenameStrategies(self.context.config.rename_strategy)(field_definition.name)
            else:
                serialization_name = field_definition.name

            transfer_field_definition = TransferDTOFieldDefinition.from_dto_field_definition(
                field_definition=field_definition,
                serialization_name=serialization_name,
                transfer_type=transfer_type,
                is_partial=self.context.config.partial,
                is_excluded=should_exclude_field(
                    field_definition=field_definition, exclude=exclude, include=include, dto_for=self.context.dto_for
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
        struct = create_struct_for_field_definitions(fqn_uid, field_definitions)
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
            obj=builtins, type=self.annotation, dec_hook=connection_context.default_deserializer, strict=False
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
                data_as_builtins=transfer_data(
                    destination_type=dict,
                    source_data=self.parse_builtins(builtins, connection_context),
                    field_definitions=self.parsed_field_definitions,
                    dto_for="data",
                    field_definition=self.context.field_definition,
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
        return transfer_data(
            self.context.model_type, builtins, self.parsed_field_definitions, "data", self.context.field_definition
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
                data_as_builtins=transfer_data(
                    dict,
                    self.parse_raw(raw, connection_context),
                    self.parsed_field_definitions,
                    "data",
                    self.context.field_definition,
                ),
            )
        return transfer_data(
            self.context.model_type,
            self.parse_raw(raw, connection_context),
            self.parsed_field_definitions,
            "data",
            self.context.field_definition,
        )

    def encode_data(self, data: Any, connection_context: ConnectionContext) -> LitestarEncodableType:
        """Encode data into a ``LitestarEncodableType``.

        Args:
            data: Data to encode.
            connection_context: Information about the active connection.

        Returns:
            Encoded data.
        """
        if self.context.wrapper_attribute_name:
            setattr(
                data,
                self.context.wrapper_attribute_name,
                transfer_data(
                    destination_type=self.transfer_model_type,
                    source_data=getattr(data, self.context.wrapper_attribute_name),
                    field_definitions=self.parsed_field_definitions,
                    dto_for="return",
                    field_definition=self.context.field_definition,
                ),
            )
            # cast() here because we take for granted that whatever ``data`` is, it must be something
            # that litestar can natively encode.
            return cast("LitestarEncodableType", data)

        return transfer_data(
            destination_type=self.transfer_model_type,
            source_data=data,
            field_definitions=self.parsed_field_definitions,
            dto_for="return",
            field_definition=self.context.field_definition,
        )

    def create_openapi_schema(self, schema_creator: SchemaCreator) -> Reference | Schema:
        """Create an openAPI schema for the given DTO."""
        return schema_creator.for_field_definition(
            FieldDefinition.from_annotation(self.annotation), dto_for=self.context.dto_for
        )

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

        if field_definition.is_union:
            return self._create_union_type(
                field_definition=field_definition,
                exclude=exclude,
                include=include,
                unique_name=unique_name,
                nested_depth=nested_depth,
            )

        if field_definition.is_tuple:
            if len(field_definition.inner_types) == 2 and field_definition.inner_types[1].annotation is Ellipsis:
                return self._create_collection_type(
                    field_definition=field_definition,
                    exclude=exclude,
                    include=include,
                    unique_name=unique_name,
                    nested_depth=nested_depth,
                )
            return self._create_tuple_type(
                field_definition=field_definition,
                exclude=exclude,
                include=include,
                unique_name=unique_name,
                nested_depth=nested_depth,
            )

        if field_definition.is_mapping:
            return self._create_mapping_type(
                field_definition=field_definition,
                exclude=exclude,
                include=include,
                unique_name=unique_name,
                nested_depth=nested_depth,
            )

        if field_definition.is_non_string_collection:
            return self._create_collection_type(
                field_definition=field_definition,
                exclude=exclude,
                include=include,
                unique_name=unique_name,
                nested_depth=nested_depth,
            )

        transfer_model: NestedFieldInfo | None = None
        if self.context.is_nested_field_predicate(field_definition):
            if nested_depth == self.context.config.max_nested_depth:
                raise NestedDepthExceededError()

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
            unique_name=_enumerate_name(unique_name, 0),
            nested_depth=nested_depth,
        )
        return CollectionType(
            field_definition=field_definition, inner_type=inner_type, has_nested=_determine_has_nested(inner_type)
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
            unique_name=_enumerate_name(unique_name, 0),
            nested_depth=nested_depth,
        )
        value_type = self._create_transfer_type(
            field_definition=inner_types[1] if inner_types else FieldDefinition.from_annotation(Any),
            exclude=exclude,
            include=include,
            field_name="1",
            unique_name=_enumerate_name(unique_name, 1),
            nested_depth=nested_depth,
        )
        return MappingType(
            field_definition=field_definition,
            key_type=key_type,
            value_type=value_type,
            has_nested=_determine_has_nested(key_type) or _determine_has_nested(value_type),
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
                unique_name=_enumerate_name(unique_name, i),
                nested_depth=nested_depth,
            )
            for i, inner_type in enumerate(field_definition.inner_types)
        )
        return TupleType(
            field_definition=field_definition,
            inner_types=inner_types,
            has_nested=any(_determine_has_nested(t) for t in inner_types),
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
                unique_name=_enumerate_name(unique_name, i),
                nested_depth=nested_depth,
            )
            for i, inner_type in enumerate(field_definition.inner_types)
        )
        return UnionType(
            field_definition=field_definition,
            inner_types=inner_types,
            has_nested=any(_determine_has_nested(t) for t in inner_types),
        )

    @staticmethod
    def _gen_unique_name_id(unique_name: str) -> str:
        # Generate a unique ID
        # Convert the ID to a short alphanumeric string
        return f"{unique_name}-{secrets.token_hex(8)}"


def _filter_nested_field(field_name_set: AbstractSet[str], field_name: str) -> AbstractSet[str]:
    """Filter a nested field name."""
    return {split[1] for s in field_name_set if (split := s.split(".", 1))[0] == field_name and len(split) > 1}


def _enumerate_name(name: str, index: int) -> str:
    """Enumerate ``name`` with ``index``."""
    return f"{name}_{index}"


def _determine_has_nested(transfer_type: SimpleType | CompositeType) -> bool:
    """Determine if a transfer type has nested types."""
    if isinstance(transfer_type, SimpleType):
        return bool(transfer_type.nested_field_info)
    return transfer_type.has_nested
