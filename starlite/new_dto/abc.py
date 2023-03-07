from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from starlite.enums import MediaType

__all__ = ("AbstractDTO",)

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from typing_extensions import Self


DataT = TypeVar("DataT")


class AbstractDTO(ABC, Generic[DataT]):
    """Base class for DTO types."""

    annotation: ClassVar[Any]

    __on_startup_called: ClassVar[bool]  # pylint: disable=unused-private-member
    """Used to bookkeep that we don't call the same ``on_startup()`` method multiple times.

    Value is set in ``starlite._signature.parsing.parse_fn_signature()``.
    """

    def __init__(self, data: DataT) -> None:
        """Create an AbstractDTO type.

        Args:
            data: the data represented by the DTO.
        """
        self.data = data

    @classmethod
    def on_startup(cls) -> None:
        """Delayed configuration callback.

        Use this to do things like type inspection on models that should not occur during compile time.
        """

    def __class_getitem__(cls, item: TypeVar | Any) -> type[Self]:
        if isinstance(item, TypeVar):
            return cls

        return type(f"{cls.__name__}[{item}]", (cls,), {"annotation": item, "__on_startup_called": False})

    @abstractmethod
    def to_encodable_type(self) -> Any:
        """Encode data held by the DTO type to a type supported by starlite serialization."""

    @classmethod
    @abstractmethod
    def from_bytes(cls, raw: bytes, media_type: MediaType | str = MediaType.JSON) -> Self:
        """Construct an instance from bytes.

        Args:
            raw: A byte representation of the DTO model.
            media_type: serialization format.

        Returns:
            AbstractDTO instance.
        """
