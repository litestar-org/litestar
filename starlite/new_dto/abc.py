from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from starlite.enums import MediaType

__all__ = ("AbstractDTO",)


if TYPE_CHECKING:
    from typing_extensions import Self

T = TypeVar("T")


class AbstractDTO(ABC, Generic[T]):
    """Required interface for supported DTO types."""

    @abstractmethod
    def to_bytes(self, media_type: MediaType | str = MediaType.JSON) -> bytes:
        """Encode data held by the DTO type to bytes.

        Args:
            media_type: serialization format.

        Raises:
            SerializationException: if media type is not supported.
        """

    @abstractmethod
    def to_model(self) -> T:
        """Construct a model from data held by the DTO type.

        Returns:
            A model instance
        """

    @classmethod
    @abstractmethod
    def from_bytes(cls, raw: bytes) -> Self:
        """Construct an instance from bytes.

        Args:
            raw: A byte representation of the DTO model.

        Returns:
            AbstractDTO instance.
        """

    @classmethod
    @abstractmethod
    def list_from_bytes(cls, raw: bytes) -> list[Self]:
        """Construct a list of instances from bytes.

        Args:
            raw: A byte representation of an array of DTO models.

        Returns:
            List of AbstractDTO instances.
        """

    @classmethod
    @abstractmethod
    def from_model(cls, model: T) -> Self:
        """Construct DTO instance from model instance.

        Args:
            model: A model instance.

        Returns:
            AbstractDTO instance.
        """
