from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import TYPE_CHECKING, Any, Generic, TypeVar

from typing_extensions import Annotated, get_args, get_origin

from starlite.enums import MediaType

from .config import DTOConfig
from .enums import Mark, Purpose
from .exc import InvalidAnnotation
from .types import DataT, FieldDefinition, NestedFieldDefinition
from .utils import parse_config_from_annotated

if TYPE_CHECKING:
    from typing import ClassVar, Generator

    from typing_extensions import Self

    from .backends.abc import AbstractDTOBackend
    from .types import FieldDefinitionsType, StarliteEncodableType

__all__ = ("AbstractDTO",)


class AbstractDTO(ABC, Generic[DataT]):
    """Base class for DTO types."""

    annotation: ClassVar[type[Any]]
    """The full annotation used to make the generic DTO concrete."""
    config: ClassVar[DTOConfig]
    """Config object to define the properties of the DTO."""
    model_type: ClassVar[type[Any]]
    """If ``annotation`` is an iterable, this is the inner type, otherwise will be the same as ``annotation``."""
    field_definitions: ClassVar[FieldDefinitionsType]
    """Field definitions parsed from the model."""
    dto_backend_type: ClassVar[type[AbstractDTOBackend]]
    """DTO backend type."""
    dto_backend: ClassVar[AbstractDTOBackend]
    """DTO backend instance."""

    _postponed_cls_init_called: ClassVar[bool]

    def __init__(self, data: DataT) -> None:
        """Create an AbstractDTO type.

        Args:
            data: the data represented by the DTO.
        """
        self.data = data

    def __class_getitem__(cls, item: TypeVar | type[Any]) -> type[Self]:
        if isinstance(item, TypeVar):
            return cls

        config: DTOConfig
        if get_origin(item) is Annotated:
            item, config = parse_config_from_annotated(item)
        else:
            config = getattr(cls, "config", DTOConfig())

        if isinstance(item, str):
            raise InvalidAnnotation("Forward references are not supported as type argument to DTO")

        cls_dict = {"config": config, "_postponed_cls_init_called": False}
        if not isinstance(item, TypeVar):
            cls_dict.update(annotation=item, model_type=cls.get_model_type(item))

        return type(f"{cls.__name__}[{item}]", (cls,), cls_dict)

    # Runtime methods

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
    def from_bytes(cls, raw: bytes, media_type: MediaType | str = MediaType.JSON) -> Self:
        """Construct an instance from bytes.

        Args:
            raw: A byte representation of the DTO model.
            media_type: serialization format.

        Returns:
            AbstractDTO instance.
        """
        parsed = cls.dto_backend.parse_raw(raw, media_type)
        return cls(data=cls.build_data(cls.annotation, parsed, cls.field_definitions))

    @classmethod
    def build_data(cls, annotation: type[Any], data: Any, field_definitions: FieldDefinitionsType) -> Any:
        """Create instance or iterable of instances of ``cls.model_type``.

        Args:
            annotation: the annotation received by the DTO on type narrowing.
            data: primitive data that has been parsed and validated via the backend.
            field_definitions: model field definitions.

        Returns:
            Data parsed into ``annotation``.
        """
        origin = get_origin(annotation)
        if origin:
            return origin(cls.build_data(cls.model_type, item, field_definitions) for item in data)

        for k, v in data.items():
            field_definition = field_definitions[k]
            if isinstance(field_definition, FieldDefinition):
                continue

            if isinstance(v, dict):
                data[k] = cls.build_data(field_definition.nested_type, v, field_definition.nested_field_definitions)
            elif isinstance(v, Iterable):
                if field_definition.origin is None:  # pragma: no cover
                    raise RuntimeError("Unexpected origin value for collection type.")
                data[k] = field_definition.origin(
                    cls.build_data(field_definition.nested_type, item, field_definition.nested_field_definitions)
                    for item in v
                )

        return annotation(**data)

    # Model generation

    @classmethod
    @abstractmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Generator[FieldDefinition, None, None]:
        """Generate ``FieldDefinition`` instances from ``model_type``.

        Yields:
            ``FieldDefinition`` instances.
        """

    @classmethod
    @abstractmethod
    def detect_nested(cls, field_definition: FieldDefinition) -> bool:
        """Return ``True`` if ``field_definition`` represents a nested model field.

        Args:
            field_definition: inspect type to determine if field definition represents a nested model.

        Returns:
            ``True`` if ``field_definition`` represents a nested model field.
        """

    @classmethod
    def parse_model(cls, model_type: Any, nested_depth: int = 0, recursive_depth: int = 0) -> FieldDefinitionsType:
        """Reduce :attr:`model_type` to :class:`FieldDefinitionsType`.

        .. important::
            Implementations must respect the :attr:`config` object. For example:
                - fields marked private must never be included in the field definitions.
                - if a ``purpose`` is declared, then read-only fields must be taken into account.
                - field mappings must be implemented.
                - additional fields must be included, subject to ``purpose``.
                - nested depth and nested recursion depth must be adhered to.

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
        defined_fields: dict[str, FieldDefinition | NestedFieldDefinition] = {}
        for field_definition in cls.generate_field_definitions(model_type):
            if cls.should_exclude_field(field_definition):
                continue

            if cls.detect_nested(field_definition):
                nested_field_definition = cls.handle_nested(field_definition, nested_depth, recursive_depth)
                if nested_field_definition is not None:
                    defined_fields[field_definition.field_name] = nested_field_definition
                continue

            defined_fields[field_definition.field_name] = field_definition
        return defined_fields

    @classmethod
    def handle_nested(
        cls, field_definition: FieldDefinition, nested_depth: int, recursive_depth: int
    ) -> NestedFieldDefinition | None:
        if nested_depth == cls.config.max_nested_depth:
            return None

        args = get_args(field_definition.field_type)
        origin = get_origin(field_definition.field_type)
        nested = NestedFieldDefinition(
            field_definition=field_definition,
            origin=origin,
            args=args,
            nested_type=args[0] if args else field_definition.field_type,
        )

        if (is_recursive := nested.is_recursive(cls.model_type)) and recursive_depth == cls.config.max_nested_recursion:
            return None

        nested.nested_field_definitions = cls.parse_model(
            nested.nested_type, nested_depth + 1, recursive_depth + is_recursive
        )
        return nested

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
    def should_exclude_field(cls, field_definition: FieldDefinition) -> bool:
        """Returns ``True`` where a field should be excluded from data transfer.

        Args:
            field_definition: defined DTO field

        Returns:
            ``True`` if the field should not be included in any data transfer.
        """
        field_name = field_definition.field_name
        dto_field = field_definition.dto_field
        excluded = field_name in cls.config.exclude
        not_included = cls.config.include and field_name not in cls.config.include
        private = dto_field and dto_field.mark is Mark.PRIVATE
        read_only_for_write = cls.config.purpose is Purpose.WRITE and dto_field and dto_field.mark is Mark.READ_ONLY
        return bool(excluded or not_included or private or read_only_for_write)

    @classmethod
    def postponed_cls_init(cls) -> None:
        """Delayed configuration callback.

        Use this to do things like type inspection on models that should not occur during compile time.
        """
        cls.field_definitions = cls.parse_model(cls.model_type)
        cls.dto_backend = cls.dto_backend_type.from_field_definitions(cls.annotation, cls.field_definitions)

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
