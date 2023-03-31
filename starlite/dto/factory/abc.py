from __future__ import annotations

from abc import ABCMeta, abstractmethod
from copy import copy
from itertools import chain
from typing import TYPE_CHECKING, Generic, Iterable, TypeVar

from typing_extensions import Annotated, Self, get_args, get_origin

from starlite.dto import AbstractDTOInterface, DataT

from .backends import AbstractDTOBackend, MsgspecDTOBackend
from .config import DTOConfig
from .enums import Mark, Purpose
from .exc import InvalidAnnotation
from .types import FieldDefinition, FieldDefinitionsType, NestedFieldDefinition
from .utils import build_data_from_struct, build_struct_from_model, parse_config_from_annotated

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator

    from starlite.connection import Request
    from starlite.enums import MediaType

__all__ = ["AbstractDTOFactory", "MsgspecBackedDTOFactory"]


class AbstractDTOFactory(AbstractDTOInterface[DataT], Generic[DataT], metaclass=ABCMeta):
    """Base class for DTO types."""

    __slots__ = ("data",)

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
    _reverse_field_mappings: ClassVar[dict[str, FieldDefinition]]

    def __init__(self, data: DataT) -> None:
        """Create an AbstractDTOFactory type.

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

        cls_dict: dict[str, Any] = {
            "config": config,
            "_postponed_cls_init_called": False,
            "_reverse_field_mappings": {},
        }
        if not isinstance(item, TypeVar):
            cls_dict.update(annotation=item, model_type=cls.get_model_type(item))

        return type(f"{cls.__name__}[{item}]", (cls,), cls_dict)

    def to_data_type(self) -> DataT:
        """Return the data held by the DTO."""
        return self.data

    @classmethod
    def from_data(cls, data: DataT) -> Self:
        """Construct an instance from data.

        Args:
            data: Data to construct the DTO from.

        Returns:
            AbstractDTOInterface instance.
        """
        return cls(data=data)

    @classmethod
    @abstractmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Generator[FieldDefinition, None, None]:
        """Generate ``FieldDefinition`` instances from ``model_type``.

        Yields:
            ``FieldDefinition`` instances.
        """

    @classmethod
    @abstractmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
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
        for field_definition in chain(cls.generate_field_definitions(model_type), cls.config.field_definitions):
            if cls.should_exclude_field(field_definition):
                continue

            if field_mapping := cls.config.field_mapping.get(field_definition.field_name):
                if isinstance(field_mapping, str):
                    cls._reverse_field_mappings[field_mapping] = field_definition
                    field_definition = copy(field_definition)  # noqa: PLW2901
                    field_definition.field_name = field_mapping
                else:
                    cls._reverse_field_mappings[field_mapping.field_name] = field_definition
                    field_definition = field_mapping  # noqa: PLW2901

            if cls.detect_nested_field(field_definition):
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
        if issubclass(get_origin(resolved_handler_annotation) or resolved_handler_annotation, AbstractDTOFactory):
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


class MsgspecBackedDTOFactory(AbstractDTOFactory[DataT], Generic[DataT], metaclass=ABCMeta):
    dto_backend_type = MsgspecDTOBackend
    dto_backend: ClassVar[MsgspecDTOBackend]

    @classmethod
    async def from_connection(cls, connection: Request[Any, Any, Any]) -> Self:
        """Construct an instance from bytes.

        Args:
            connection: A byte representation of the DTO model.

        Returns:
            AbstractDTOFactory instance.
        """
        parsed = cls.dto_backend.parse_raw(await connection.body(), connection.content_type[0])
        return cls(data=build_data_from_struct(cls.model_type, parsed, cls.field_definitions))  # type:ignore[arg-type]

    def to_encodable_type(self, media_type: str | MediaType, request: Request[Any, Any, Any]) -> Any:
        if isinstance(self.data, self.model_type):
            return build_struct_from_model(self.data, self.dto_backend.data_container_type)
        type_ = get_origin(self.annotation) or self.annotation
        return type_(
            build_struct_from_model(datum, self.dto_backend.data_container_type)
            for datum in self.data  # pyright:ignore
        )
