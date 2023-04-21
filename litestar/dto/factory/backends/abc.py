"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
back again, to bytes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar._openapi.schema_generation import create_schema
from litestar._signature.field import SignatureField

from .utils import build_annotation_for_backend

if TYPE_CHECKING:
    from typing import Any

    from litestar.connection import Request
    from litestar.dto.factory.types import FieldDefinitionsType
    from litestar.enums import MediaType
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType
    from litestar.utils.signature import ParsedType

__all__ = ("AbstractDTOBackend", "BackendContext")

BackendT = TypeVar("BackendT")


@dataclass
class BackendContext:
    """Context required by DTO backends to perform their work."""

    parsed_type: ParsedType
    field_definitions: FieldDefinitionsType
    model_type: type[Any]


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
    def parse_raw(self, raw: bytes, media_type: MediaType | str) -> Any:
        """Parse raw bytes into primitive python types.

        Args:
            raw: bytes
            media_type: encoding of raw data

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
    def populate_data_from_raw(self, raw: bytes, media_type: MediaType | str) -> Any:
        """Parse raw bytes into instance of `model_type`.

        Args:
            model_type: Type of model to populate.
            raw: bytes
            media_type: encoding of raw data

        Returns:
            Instance or collection of ``model_type`` instances.
        """

    @abstractmethod
    def encode_data(self, data: Any, connection: Request[Any, Any, Any]) -> LitestarEncodableType:
        """Encode data into a ``LitestarEncodableType``.

        Args:
            data: Data to encode.
            connection: Connection - can be used for content negotiation.

        Returns:
            Encoded data.
        """

    def create_openapi_schema(self, generate_examples: bool, schemas: dict[str, Schema]) -> Reference | Schema:
        """Create a RequestBody model for the given RouteHandler or return None."""
        field = SignatureField.create(self.annotation)
        return create_schema(field=field, generate_examples=generate_examples, plugins=[], schemas=schemas)
