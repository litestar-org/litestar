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

    from starlite.dto.factory.types import FieldDefinitionsType
    from starlite.enums import MediaType

__all__ = ("AbstractDTOBackend",)

BackendT = TypeVar("BackendT")


class AbstractDTOBackend(ABC, Generic[BackendT]):
    __slots__ = ("data_container_type", "annotation")

    def __init__(self, annotation: type[Any], data_container_type: type[BackendT]) -> None:
        """Create dto backend instance.

        Args:
            annotation: Annotation received by the DTO.
            data_container_type: Parsing/validation/serialization model.
        """
        self.data_container_type = data_container_type
        self.annotation = build_annotation_for_backend(annotation, data_container_type)

    @classmethod
    @abstractmethod
    def from_field_definitions(cls, annotation: type[Any], field_definitions: FieldDefinitionsType) -> Self:
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
