"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
back again, to bytes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar._openapi.schema_generation import create_schema
from litestar._signature.field import SignatureField

from .types import NestedFieldDefinition, TransferFieldDefinition
from .utils import RenameStrategies, build_annotation_for_backend, get_model_type, should_exclude_field

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
        "model_type",
        "nested_field_detector",
        "parsed_type",
    )

    def __init__(
        self,
        dto_config: DTOConfig,
        dto_for: ForType,
        parsed_type: ParsedType,
        field_definition_generator: Callable[[Any], Generator[FieldDefinition, None, None]],
        nested_field_detector: Callable[[FieldDefinition], bool],
        model_type: type[Any],
    ) -> None:
        """Create a backend context.

        Args:
            dto_config: DTO config.
            dto_for: "data" or "return"
            parsed_type: Parsed type.
            field_definition_generator: Generator that produces
                :class:`FieldDefinition <.dto.factory.types.FieldDefinition>` instances given ``model_type``.
            nested_field_detector: Function that detects if a field is nested.
            model_type: Model type.
        """
        self.config: Final[DTOConfig] = dto_config
        self.dto_for: Final[ForType] = dto_for
        self.parsed_type: Final[ParsedType] = parsed_type
        self.field_definition_generator: Final[
            Callable[[Any], Generator[FieldDefinition, None, None]]
        ] = field_definition_generator
        self.nested_field_detector: Final[Callable[[FieldDefinition], bool]] = nested_field_detector
        self.model_type: Final[type[Any]] = model_type


class AbstractDTOBackend(ABC, Generic[BackendT]):
    __slots__ = (
        "annotation",
        "context",
        "data_container_type",
        "parsed_field_definitions",
        "reverse_name_map",
    )

    def __init__(self, context: BackendContext) -> None:
        """Create dto backend instance.

        Args:
            context: context of the type represented by this backend.
        """
        self.context = context
        self.parsed_field_definitions = self.parse_model(context.model_type, context.config.exclude)
        self.reverse_name_map = {
            f.serialization_name: f.name for f in self.parsed_field_definitions.values() if f.serialization_name
        }
        self.data_container_type = self.create_data_container_type(context)
        self.annotation = build_annotation_for_backend(context.parsed_type.annotation, self.data_container_type)

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
        defined_fields: dict[str, TransferFieldDefinition | NestedFieldDefinition] = {}
        for field_definition in self.context.field_definition_generator(model_type):
            if should_exclude_field(field_definition, exclude, self.context.dto_for):
                continue

            if rename := self.context.config.rename_fields.get(field_definition.name):
                serialization_name = rename
            elif self.context.config.rename_strategy:
                serialization_name = RenameStrategies(self.context.config.rename_strategy)(field_definition.name)
            else:
                serialization_name = field_definition.name

            transfer_field_definition = TransferFieldDefinition(
                name=field_definition.name,
                default=field_definition.default,
                parsed_type=field_definition.parsed_type,
                default_factory=field_definition.default_factory,
                serialization_name=serialization_name,
            )

            if self.context.nested_field_detector(transfer_field_definition):
                if nested_depth == self.context.config.max_nested_depth:
                    continue

                nested_exclude = {split[1] for s in exclude if (split := s.split(".", 1))[0] == field_definition.name}
                nested_type = get_model_type(transfer_field_definition.annotation)
                nested = NestedFieldDefinition(
                    field_definition=transfer_field_definition,
                    nested_type=nested_type,
                    nested_field_definitions=self.parse_model(nested_type, nested_exclude, nested_depth + 1),
                )
                defined_fields[transfer_field_definition.name] = nested
            else:
                defined_fields[transfer_field_definition.name] = transfer_field_definition
        return defined_fields

    @abstractmethod
    def create_data_container_type(self, context: BackendContext) -> type[BackendT]:
        """Create a data container type to represent the context type.

        Args:
            context: Context of the type to create a data container for.

        Returns:
            A ``BackendT`` class.
        """

    @abstractmethod
    def parse_raw(self, raw: bytes, connection_context: ConnectionContext) -> Any:
        """Parse raw bytes into primitive python types.

        Args:
            raw: bytes
            connection_context: Information about the active connection.

        Returns:
            The raw bytes parsed into primitive python types.
        """

    @abstractmethod
    def populate_data_from_builtins(self, data: Any) -> Any:
        """Populate model instance from builtin types.

        Args:
            model_type: Type of model to populate.
            data: Builtin type.

        Returns:
            Instance or collection of ``model_type`` instances.
        """

    @abstractmethod
    def populate_data_from_raw(self, raw: bytes, connection_context: ConnectionContext) -> Any:
        """Parse raw bytes into instance of `model_type`.

        Args:
            raw: bytes
            connection_context: Information about the active connection.

        Returns:
            Instance or collection of ``model_type`` instances.
        """

    @abstractmethod
    def encode_data(self, data: Any, connection_context: ConnectionContext) -> LitestarEncodableType:
        """Encode data into a ``LitestarEncodableType``.

        Args:
            data: Data to encode.
            connection_context: Information about the active connection.

        Returns:
            Encoded data.
        """

    def create_openapi_schema(self, generate_examples: bool, schemas: dict[str, Schema]) -> Reference | Schema:
        """Create a RequestBody model for the given RouteHandler or return None."""
        field = SignatureField.create(self.annotation)
        return create_schema(field=field, generate_examples=generate_examples, plugins=[], schemas=schemas)
