from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from typing_extensions import get_args, get_origin

from starlite.enums import MediaType

__all__ = ("AbstractDTO",)

if TYPE_CHECKING:
    from typing import ClassVar

    from typing_extensions import Self


DataT = TypeVar("DataT")
StarliteEncodableType = Any


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

        return type(
            f"{cls.__name__}[{item}]",
            (cls,),
            {"annotation": item, "model_type": cls.get_model_type(item), "_postponed_cls_init_called": False},
        )

    @staticmethod
    def get_model_type(item: type) -> Any:
        """Get model type represented by the DTO.

        Unwraps iterable annotation.

        Args:
            item: any type.

        Returns:
            The model type that is represented by the DTO.
        """
        if issubclass(get_origin(item) or item, Iterable):
            return get_args(item)[0]
        return item

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

        if not issubclass(cls.get_model_type(resolved_dto_annotation), cls.model_type):
            raise ValueError("DTO handler annotation mismatch")

        if not cls._postponed_cls_init_called:
            cls._postponed_cls_init_called = True
            cls.postponed_cls_init()

    @abstractmethod
    def to_encodable_type(self, media_type: str | MediaType) -> bytes | StarliteEncodableType:
        """Encode data held by the DTO type to a type supported by starlite serialization.

        Can return either bytes or a type that Starlite can return to bytes.

        If returning bytes, must respect ``media_type``.

        If media type not supported raise `SerializationException`.

        If returning a ``StarliteEncodableType``, ignore ``media_type``.

        Args:
            media_type: expected encoding type of serialized data

        Returns:
            Either ``bytes`` or a type that Starlite can convert to bytes.
        """

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
