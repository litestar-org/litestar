"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
back again, to bytes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar._openapi.schema_generation import create_schema
from litestar._signature.field import SignatureField
from litestar.utils.helpers import get_fully_qualified_class_name

from .types import (
    CollectionType,
    CompositeType,
    MappingType,
    NestedFieldInfo,
    SimpleType,
    TransferFieldDefinition,
    TupleType,
    UnionType,
)
from .utils import (
    RenameStrategies,
    build_annotation_for_backend,
    should_exclude_field,
    transfer_data,
)

if TYPE_CHECKING:
    from typing import AbstractSet, Any, Callable, Final, Generator

    from litestar.dto.factory import DTOConfig
    from litestar.dto.factory.types import FieldDefinition
    from litestar.dto.interface import ConnectionContext
    from litestar.dto.types import ForType
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType
    from litestar.utils.signature import ParsedType

    from .types import FieldDefinitionsType

__all__ = ("AbstractDTOBackend", "BackendContext")

BackendT = TypeVar("BackendT")


class BackendContext:
    """Context required by DTO backends to perform their work."""

    __slots__ = (
        "config",
        "dto_for",
        "field_definition_generator",
        "is_nested_field_predicate",
        "model_type",
        "parsed_type",
    )

    def __init__(
        self,
        dto_config: DTOConfig,
        dto_for: ForType,
        parsed_type: ParsedType,
        field_definition_generator: Callable[[Any], Generator[FieldDefinition, None, None]],
        is_nested_field_predicate: Callable[[ParsedType], bool],
        model_type: type[Any],
    ) -> None:
        """Create a backend context.

        Args:
            dto_config: DTO config.
            dto_for: "data" or "return"
            parsed_type: Parsed type.
            field_definition_generator: Generator that produces
                :class:`FieldDefinition <.dto.factory.types.FieldDefinition>` instances given ``model_type``.
            is_nested_field_predicate: Function that detects if a field is nested.
            model_type: Model type.
        """
        self.config: Final[DTOConfig] = dto_config
        self.dto_for: Final[ForType] = dto_for
        self.parsed_type: Final[ParsedType] = parsed_type
        self.field_definition_generator: Final[
            Callable[[Any], Generator[FieldDefinition, None, None]]
        ] = field_definition_generator
        self.is_nested_field_predicate: Final[Callable[[ParsedType], bool]] = is_nested_field_predicate
        self.model_type: Final[type[Any]] = model_type


class NestedDepthExceededError(Exception):
    """Raised when a nested type exceeds the maximum allowed depth.

    Not an exception that is intended to be raised into userland, rather a signal to the process that is iterating over
    the field definitions that the current field should be skipped.
    """


class AbstractDTOBackend(ABC, Generic[BackendT]):
    __slots__ = (
        "annotation",
        "context",
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
        self.parsed_field_definitions = self.parse_model(context.model_type, context.config.exclude)
        self.transfer_model_type = self.create_transfer_model_type(
            get_fully_qualified_class_name(context.model_type), self.parsed_field_definitions
        )
        self.annotation = build_annotation_for_backend(context.parsed_type.annotation, self.transfer_model_type)

    def parse_model(
        self,
        model_type: Any,
        exclude: AbstractSet[str],
        nested_depth: int = 0,
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
            if should_exclude_field(field_definition, exclude, self.context.dto_for):
                continue

            try:
                transfer_type = self._create_transfer_type(
                    field_definition.parsed_type,
                    exclude,
                    field_definition.name,
                    field_definition.unique_name(),
                    nested_depth,
                )
            except NestedDepthExceededError:
                continue

            if rename := self.context.config.rename_fields.get(field_definition.name):
                serialization_name = rename
            elif self.context.config.rename_strategy:
                serialization_name = RenameStrategies(self.context.config.rename_strategy)(field_definition.name)
            else:
                serialization_name = field_definition.name

            transfer_field_definition = TransferFieldDefinition.from_field_definition(
                field_definition=field_definition,
                serialization_name=serialization_name,
                transfer_type=transfer_type,
            )
            defined_fields.append(transfer_field_definition)
        return tuple(defined_fields)

    @abstractmethod
    def create_transfer_model_type(self, unique_name: str, field_definitions: FieldDefinitionsType) -> type[BackendT]:
        """Create a model for data transfer.

        Args:
            unique_name: name for the type that should be unique across all transfer types.
            field_definitions: field definitions for the container type.

        Returns:
            A ``BackendT`` class.
        """

    @abstractmethod
    def parse_raw(self, raw: bytes, connection_context: ConnectionContext) -> Any:
        """Parse raw bytes into transfer model type.

        Args:
            raw: bytes
            connection_context: Information about the active connection.

        Returns:
            The raw bytes parsed into transfer model type.
        """

    @abstractmethod
    def parse_builtins(self, builtins: Any, connection_context: ConnectionContext) -> Any:
        """Parse builtin types into transfer model type.

        Args:
            builtins: Builtin type.
            connection_context: Information about the active connection.

        Returns:
            The builtin type parsed into transfer model type.
        """

    def populate_data_from_builtins(self, builtins: Any, connection_context: ConnectionContext) -> Any:
        """Populate model instance from builtin types.

        Args:
            builtins: Builtin type.
            connection_context: Information about the active connection.

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        return transfer_data(
            self.context.model_type,
            self.parse_builtins(builtins, connection_context),
            self.parsed_field_definitions,
            "data",
        )

    def populate_data_from_raw(self, raw: bytes, connection_context: ConnectionContext) -> Any:
        """Parse raw bytes into instance of `model_type`.

        Args:
            raw: bytes
            connection_context: Information about the active connection.

        Returns:
            Instance or collection of ``model_type`` instances.
        """
        return transfer_data(
            self.context.model_type, self.parse_raw(raw, connection_context), self.parsed_field_definitions, "data"
        )

    def encode_data(self, data: Any, connection_context: ConnectionContext) -> LitestarEncodableType:
        """Encode data into a ``LitestarEncodableType``.

        Args:
            data: Data to encode.
            connection_context: Information about the active connection.

        Returns:
            Encoded data.
        """
        return transfer_data(
            self.transfer_model_type, data, self.parsed_field_definitions, "return"  # type: ignore[arg-type]
        )

    def create_openapi_schema(self, generate_examples: bool, schemas: dict[str, Schema]) -> Reference | Schema:
        """Create a RequestBody model for the given RouteHandler or return None."""
        field = SignatureField.create(self.annotation)
        return create_schema(field=field, generate_examples=generate_examples, plugins=[], schemas=schemas)

    def _create_transfer_type(
        self, parsed_type: ParsedType, exclude: AbstractSet[str], field_name: str, unique_name: str, nested_depth: int
    ) -> CompositeType | SimpleType:
        exclude = _filter_exclude(exclude, field_name)

        if parsed_type.is_union:
            return self._create_union_type(parsed_type, exclude, unique_name, nested_depth)

        if parsed_type.is_tuple:
            if len(parsed_type.inner_types) == 2 and parsed_type.inner_types[1].annotation is Ellipsis:
                return self._create_collection_type(parsed_type, exclude, unique_name, nested_depth)
            return self._create_tuple_type(parsed_type, exclude, unique_name, nested_depth)

        if parsed_type.is_mapping:
            return self._create_mapping_type(parsed_type, exclude, unique_name, nested_depth)

        if parsed_type.is_collection:
            return self._create_collection_type(parsed_type, exclude, unique_name, nested_depth)

        transfer_model: NestedFieldInfo | None = None
        if self.context.is_nested_field_predicate(parsed_type):
            if nested_depth == self.context.config.max_nested_depth:
                raise NestedDepthExceededError()

            nested_field_definitions = self.parse_model(parsed_type.annotation, exclude, nested_depth + 1)
            transfer_model = NestedFieldInfo(
                model=self.create_transfer_model_type(unique_name, nested_field_definitions),
                field_definitions=nested_field_definitions,
            )

        return SimpleType(parsed_type, nested_field_info=transfer_model)

    def _create_collection_type(
        self, parsed_type: ParsedType, exclude: AbstractSet[str], unique_name: str, nested_depth: int
    ) -> CollectionType:
        inner_type = self._create_transfer_type(
            parsed_type=parsed_type.inner_types[0],
            exclude=exclude,
            field_name="0",
            unique_name=_enumerate_name(unique_name, 0),
            nested_depth=nested_depth,
        )
        return CollectionType(
            parsed_type=parsed_type, inner_type=inner_type, has_nested=_determine_has_nested(inner_type)
        )

    def _create_mapping_type(
        self, parsed_type: ParsedType, exclude: AbstractSet[str], unique_name: str, nested_depth: int
    ) -> MappingType:
        key_type = self._create_transfer_type(
            parsed_type=parsed_type.inner_types[0],
            exclude=exclude,
            field_name="0",
            unique_name=_enumerate_name(unique_name, 0),
            nested_depth=nested_depth,
        )
        value_type = self._create_transfer_type(
            parsed_type=parsed_type.inner_types[1],
            exclude=exclude,
            field_name="1",
            unique_name=_enumerate_name(unique_name, 1),
            nested_depth=nested_depth,
        )
        return MappingType(
            parsed_type=parsed_type,
            key_type=key_type,
            value_type=value_type,
            has_nested=_determine_has_nested(key_type) or _determine_has_nested(value_type),
        )

    def _create_tuple_type(
        self, parsed_type: ParsedType, exclude: AbstractSet[str], unique_name: str, nested_depth: int
    ) -> TupleType:
        inner_types = tuple(
            self._create_transfer_type(
                parsed_type=inner_type,
                exclude=exclude,
                field_name=str(i),
                unique_name=_enumerate_name(unique_name, i),
                nested_depth=nested_depth,
            )
            for i, inner_type in enumerate(parsed_type.inner_types)
        )
        return TupleType(
            parsed_type=parsed_type,
            inner_types=inner_types,
            has_nested=any(_determine_has_nested(t) for t in inner_types),
        )

    def _create_union_type(
        self, parsed_type: ParsedType, exclude: AbstractSet[str], unique_name: str, nested_depth: int
    ) -> UnionType:
        inner_types = tuple(
            self._create_transfer_type(
                parsed_type=inner_type,
                exclude=exclude,
                field_name=str(i),
                unique_name=_enumerate_name(unique_name, i),
                nested_depth=nested_depth,
            )
            for i, inner_type in enumerate(parsed_type.inner_types)
        )
        return UnionType(
            parsed_type=parsed_type,
            inner_types=inner_types,
            has_nested=any(_determine_has_nested(t) for t in inner_types),
        )


def _filter_exclude(exclude: AbstractSet[str], field_name: str) -> AbstractSet[str]:
    """Filter exclude set to only include exclusions for the given field name."""
    return {split[1] for s in exclude if (split := s.split(".", 1))[0] == field_name}


def _enumerate_name(name: str, index: int) -> str:
    """Enumerate ``name`` with ``index``."""
    return f"{name}_{index}"


def _determine_has_nested(transfer_type: SimpleType | CompositeType) -> bool:
    """Determine if a transfer type has nested types."""
    if isinstance(transfer_type, SimpleType):
        return bool(transfer_type.nested_field_info)
    return transfer_type.has_nested
