"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
back again, to bytes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar._openapi.schema_generation import create_schema
from litestar._signature.field import SignatureField

from .utils import build_annotation_for_backend

if TYPE_CHECKING:
    from typing import Any, Final

    from litestar.dto.factory.types import FieldDefinitionsType
    from litestar.dto.interface import ConnectionContext
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType
    from litestar.utils.signature import ParsedType

__all__ = ("AbstractDTOBackend", "BackendContext")

BackendT = TypeVar("BackendT")


class BackendContext:
    """Context required by DTO backends to perform their work."""

    __slots__ = ("parsed_type", "field_definitions", "model_type", "reverse_name_map")

    def __init__(self, parsed_type: ParsedType, field_definitions: FieldDefinitionsType, model_type: type[Any]) -> None:
        """Create a backend context.

        Args:
            parsed_type: Parsed type.
            field_definitions: Field definitions.
            model_type: Model type.
        """
        self.parsed_type: Final[ParsedType] = parsed_type
        self.field_definitions: Final[FieldDefinitionsType] = field_definitions
        self.model_type: Final[type[Any]] = model_type
        self.reverse_name_map = {
            f.serialization_name: f.name for f in field_definitions.values() if f.serialization_name
        }


class AbstractDTOBackend(ABC, Generic[BackendT]):
    __slots__ = (
        "data_container_type",
        "annotation",
        "context",
    )

    def __init__(self, context: BackendContext) -> None:
        """Create dto backend instance.

        Args:
            context: context of the type represented by this backend.
        """
        self.context = context
        self.data_container_type = self.create_data_container_type(context)
        self.annotation = build_annotation_for_backend(context.parsed_type.annotation, self.data_container_type)

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
