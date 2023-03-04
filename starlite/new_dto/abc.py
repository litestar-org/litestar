from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

if TYPE_CHECKING:
    from typing_extensions import Self

T = TypeVar("T")


class AbstractDTO(ABC, Generic[T]):
    """Required interface for supported DTO types."""

    @abstractmethod
    def to_bytes(self) -> bytes:
        """Bytes representation of the data held by the DTO type."""

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
