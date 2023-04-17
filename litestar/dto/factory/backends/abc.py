"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
and back again, to bytes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from .utils import build_annotation_for_backend

if TYPE_CHECKING:
    from typing import Any, Collection

    from typing_extensions import Self

    from litestar.connection import Request
    from litestar.dto.factory.types import FieldDefinitionsType
    from litestar.enums import MediaType
    from litestar.types.serialization import LitestarEncodableType
    from litestar.utils.signature import ParsedType

__all__ = ("AbstractDTOBackend",)

T = TypeVar("T")
BackendT = TypeVar("BackendT")


class AbstractDTOBackend(ABC, Generic[BackendT]):
    __slots__ = (
        "data_container_type",
        "annotation",
        "field_definitions",
        "parsed_type",
    )

    def __init__(
        self, parsed_type: ParsedType, data_container_type: type[BackendT], field_definitions: FieldDefinitionsType
    ) -> None:
        """Create dto backend instance.

        Args:
            parsed_type: Annotation received by the DTO.
            data_container_type: Parsing/validation/serialization model.
            field_definitions: Info about the model fields that should be included in transfer data.
        """
        self.data_container_type = data_container_type
        self.annotation = build_annotation_for_backend(parsed_type.annotation, data_container_type)
        self.field_definitions = field_definitions
        self.parsed_type = parsed_type

    @classmethod
    @abstractmethod
    def from_field_definitions(cls, annotation: ParsedType, field_definitions: FieldDefinitionsType) -> Self:
        """Create a backend instance per model field definitions and annotation.

        The annotation is required in order to detect if the backend is representing scalar or sequence data.

        Args:
            annotation: DTO parameter annotation.
            field_definitions: Info about the model fields that should be included in transfer data.

        Returns:
            A DTO backend instance.
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
    def populate_data_from_raw(self, model_type: type[T], raw: bytes, media_type: MediaType | str) -> T | Collection[T]:
        """Parse raw bytes into instance of `model_type`.

        Args:
            model_type: Type of model to populate.
            raw: bytes
            media_type: encoding of raw data
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
