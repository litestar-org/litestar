from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from typing_extensions import Annotated, get_args, get_origin

from starlite.enums import MediaType

from .exc import InvalidAnnotation
from .config import DTOConfig
from .types import DataT

__all__ = ("AbstractDTO",)

if TYPE_CHECKING:
    from typing import ClassVar

    from typing_extensions import Self

    from .types import FieldDefinitionsType, StarliteEncodableType


class AbstractDTO(ABC, Generic[DataT]):
    """Base class for DTO types."""

    annotation: ClassVar[Any]
    """The full annotation used to make the generic DTO concrete."""
    config: ClassVar[DTOConfig]
    """Config object to define the properties of the DTO."""
    model_type: ClassVar[Any]
    """If ``annotation`` is an iterable, this is the inner type, otherwise will be the same as ``annotation``."""

    _postponed_cls_init_called: ClassVar[bool]

    def __init__(self, data: DataT) -> None:
        """Create an AbstractDTO type.

        Args:
            data: the data represented by the DTO.
        """
        self.data = data

    def __class_getitem__(cls, item: TypeVar | type | type[Annotated[TypeVar | type, DTOConfig, ...]]) -> type[Self]:
        if isinstance(item, TypeVar):
            return cls

        config: DTOConfig
        if get_origin(item) is Annotated:
            item, expected_config, *_ = get_args(item)
            if not isinstance(expected_config, DTOConfig):
                raise InvalidAnnotation("Annotation metadata must be an instance of `DTOConfig`.")
            config = expected_config
        else:
            config = getattr(cls, "config", DTOConfig())

        if isinstance(item, str):
            raise InvalidAnnotation("Forward references are not supported as type argument to DTO")

        cls_dict = {"config": config, "_postponed_cls_init_called": False}
        if not isinstance(item, TypeVar):
            cls_dict.update(annotation=item, model_type=cls.get_model_type(item))

        return type(f"{cls.__name__}[{item}]", (cls,), cls_dict)

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
    @abstractmethod
    def parse_model(cls) -> FieldDefinitionsType:
        """Reduce :attr:`model_type` to :class:`FieldDefinitionsType`.

        .. important::
            Implementations must respect the :attr:`config` object. For example:
                - fields marked private must never be included in the field definitions.
                - if a ``purpose`` is declared, then read-only fields must be taken into account.
                - field mappings must be implemented.
                - additions fields must be included, subject to ``purpose``.

        Returns:
            Fields for data transfer.

            Key is the name of the new field, and value is a tuple of type and default value pairs.

            Add a new field called "new_field", that is a string, and required:
            {"new_field": (str, ...)}

            Add a new field called "new_field", that is a string, and not-required:
            {"new_field": (str, "default")}

            Add a new field called "new_field", that may be `None`:
            {"new_field": (str | None, None)}
        """

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

        if not issubclass(handler_type := cls.get_model_type(resolved_dto_annotation), cls.model_type):
            raise InvalidAnnotation(
                f"DTO annotation mismatch: DTO narrowed with '{cls.model_type}', handler type is '{handler_type}'"
            )

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
