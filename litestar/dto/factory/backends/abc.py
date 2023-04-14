"""DTO backends do the heavy lifting of decoding and validating raw bytes into domain models, and
and back again, to bytes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from .utils import build_annotation_for_backend

if TYPE_CHECKING:
    from typing import Any

    from typing_extensions import Self

    from litestar.dto.factory.types import FieldDefinitionsType
    from litestar.enums import MediaType
    from litestar.utils.signature import ParsedType

__all__ = ("AbstractDTOBackend",)

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
