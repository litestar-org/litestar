from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Generic, TypeVar

from typing_extensions import get_args, get_origin

from starlite.enums import MediaType

__all__ = ("AbstractDTO",)

if TYPE_CHECKING:
    from typing import Any, ClassVar

    from typing_extensions import Self


DataT = TypeVar("DataT")


class AbstractDTO(ABC, Generic[DataT]):
    """Base class for DTO types."""

    annotation: ClassVar[Any]
    model_type: Any

    _postponed_cls_init_called: ClassVar[bool]
    """Used to bookkeep that logic in the ``postponed_cls_init()`` method is not executed multiple times."""

    def __init__(self, data: DataT) -> None:
        """Create an AbstractDTO type.

        Args:
            data: the data represented by the DTO.
        """
        self.data = data

    def __class_getitem__(cls, item: TypeVar | Any) -> type[Self]:
        if isinstance(item, TypeVar):
            return cls

        if isinstance(item, str):
            raise TypeError("Forward reference not supported as type argument to DTO")

        if issubclass(get_origin(item) or item, Iterable):
            model_type = get_args(item)[0]
        else:
            model_type = item

        return type(
            f"{cls.__name__}[{item}]",
            (cls,),
            {"annotation": item, "model_type": model_type, "_postponed_cls_init_called": False},
        )

    @classmethod
    def postponed_cls_init(cls) -> None:
        """Delayed configuration callback.

        Use this to do things like type inspection on models that should not occur during compile time.
        """

    @classmethod
    def on_startup(cls, resolved_handler_annotation: Any) -> None:
        """Do something each time the DTO type is encountered during signature modelling.

        Args:
            resolved_handler_annotation: Resolved annotation of the handler function.
        """
        if issubclass(get_origin(resolved_handler_annotation) or resolved_handler_annotation, AbstractDTO):
            resolved_dto_annotation = resolved_handler_annotation.annotation
        else:
            resolved_dto_annotation = resolved_handler_annotation

        if resolved_dto_annotation != cls.annotation:
            raise ValueError("DTO handler annotation mismatch")

        if not cls._postponed_cls_init_called:
            cls._postponed_cls_init_called = True
            cls.postponed_cls_init()

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
