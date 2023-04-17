from __future__ import annotations

from abc import ABCMeta, abstractmethod
from itertools import chain
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar.dto.factory.backends import MsgspecDTOBackend
from litestar.dto.interface import DTOInterface
from litestar.types.builtin_types import NoneType
from litestar.utils.signature import ParsedType

from .config import DTOConfig
from .exc import InvalidAnnotation
from .field import Mark
from .types import FieldDefinition, FieldDefinitionsType, NestedFieldDefinition
from .utils import parse_configs_from_annotation

if TYPE_CHECKING:
    from typing import Any, ClassVar, Collection, Generator, Literal, TypeAlias

    from typing_extensions import Self

    from litestar.connection import Request
    from litestar.dto.types import ForType
    from litestar.handlers import BaseRouteHandler
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType

    from .backends import AbstractDTOBackend

__all__ = ["AbstractDTOFactory"]

AnyRequest: TypeAlias = "Request[Any, Any, Any]"
DataT = TypeVar("DataT")


class AbstractDTOFactory(DTOInterface, Generic[DataT], metaclass=ABCMeta):
    """Base class for DTO types."""

    __slots__ = (
        "_connection",
        "_data",
    )

    configs: ClassVar[tuple[DTOConfig, ...]]
    """Config objects to define properties of the DTO."""
    model_type: ClassVar[type[Any]]
    """If ``annotation`` is an iterable, this is the inner type, otherwise will be the same as ``annotation``."""

    _reverse_field_mappings: ClassVar[dict[str, FieldDefinition]]
    _type_config_backend_map: ClassVar[dict[tuple[ParsedType, DTOConfig], AbstractDTOBackend]]
    _handler_config_backend_map: ClassVar[dict[tuple[ForType, BaseRouteHandler, DTOConfig], AbstractDTOBackend]]

    def __init__(self, data: DataT | Collection[DataT], connection: AnyRequest) -> None:
        """Create an AbstractDTOFactory type.

        Args:
            data: the data represented by the DTO.
            connection: Request object.
        """
        self._data = data
        self._connection = connection

    def __class_getitem__(cls, annotation: Any) -> type[Self]:
        parsed_type = ParsedType(annotation)

        if (parsed_type.is_optional and len(parsed_type.args) > 2) or (
            parsed_type.is_union and not parsed_type.is_optional
        ):
            raise InvalidAnnotation(
                "Unions are currently not supported as type argument to DTO. Want this? Open an issue."
            )

        if parsed_type.is_forward_ref:
            raise InvalidAnnotation("Forward references are not supported as type argument to DTO")

        configs = parse_configs_from_annotation(parsed_type)

        if parsed_type.is_type_var and not configs:
            return cls

        cls_dict: dict[str, Any] = {
            "configs": configs or (DTOConfig(),),
            "_reverse_field_mappings": {},
            "_type_config_backend_map": {},
            "_handler_config_backend_map": {},
        }
        if not parsed_type.is_type_var:
            cls_dict.update(model_type=parsed_type.annotation)

        return type(f"{cls.__name__}[{annotation}]", (cls,), cls_dict)

    def to_data_type(self) -> DataT | Collection[DataT]:
        """Return the data held by the DTO."""
        return self._data

    def to_encodable_type(self) -> LitestarEncodableType:
        backend = self.get_backend("return", self._connection.route_handler)
        return backend.encode_data(self._data, self._connection)

    @classmethod
    def from_data(cls, data: DataT | Collection[DataT], connection: AnyRequest) -> Self:
        """Construct an instance from data.

        Args:
            data: Data to construct the DTO from.
            connection: Request object.

        Returns:
            AbstractDTOInterface instance.
        """
        return cls(data=data, connection=connection)

    @classmethod
    def from_bytes(cls, raw: bytes, connection: AnyRequest) -> Self:
        """Construct an instance from bytes.

        Args:
            raw: Raw connection data.
            connection: A byte representation of the DTO model.

        Returns:
            AbstractDTOFactory instance.
        """
        backend = cls.get_backend("data", connection.route_handler)
        return cls(
            data=backend.populate_data_from_raw(cls.model_type, raw, connection.content_type[0]), connection=connection
        )

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
    def parse_model(
        cls,
        model_type: Any,
        config: DTOConfig,
        dto_for: ForType,
        nested_depth: int = 0,
        recursive_depth: int = 0,
    ) -> FieldDefinitionsType:
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
        for field_definition in chain(cls.generate_field_definitions(model_type), config.field_definitions):
            if cls.should_exclude_field(field_definition, config, dto_for):
                continue

            if field_mapping := config.field_mapping.get(field_definition.name):
                if isinstance(field_mapping, str):
                    cls._reverse_field_mappings[field_mapping] = field_definition
                    field_definition = field_definition.copy_with(name=field_mapping)  # noqa: PLW2901
                else:
                    cls._reverse_field_mappings[field_mapping.name] = field_definition
                    field_definition = field_mapping  # noqa: PLW2901

            if cls.detect_nested_field(field_definition):
                nested_field_definition = cls.handle_nested(
                    field_definition, nested_depth, recursive_depth, config, dto_for
                )
                if nested_field_definition is not None:
                    defined_fields[field_definition.name] = nested_field_definition
                continue

            defined_fields[field_definition.name] = field_definition
        return defined_fields

    @classmethod
    def handle_nested(
        cls,
        field_definition: FieldDefinition,
        nested_depth: int,
        recursive_depth: int,
        config: DTOConfig,
        dto_for: ForType,
    ) -> NestedFieldDefinition | None:
        if nested_depth == config.max_nested_depth:
            return None

        nested = NestedFieldDefinition(
            field_definition=field_definition,
            nested_type=cls.get_model_type(field_definition.annotation),
        )

        if (is_recursive := nested.is_recursive(cls.model_type)) and recursive_depth == config.max_nested_recursion:
            return None

        nested.nested_field_definitions = cls.parse_model(
            nested.nested_type, config, dto_for, nested_depth + 1, recursive_depth + is_recursive
        )
        return nested

    @staticmethod
    def get_model_type(annotation: type) -> Any:
        """Get model type represented by the DTO.

        If ``annotation`` is a collection, then the inner type is returned.

        Args:
            annotation: any type.

        Returns:
            The model type that is represented by the DTO.
        """
        parsed_type = ParsedType(annotation)
        if parsed_type.is_collection:
            return parsed_type.inner_types[0].annotation
        if parsed_type.is_optional:
            return next(t for t in parsed_type.inner_types if t.annotation is not NoneType).annotation
        return parsed_type.annotation

    @classmethod
    def should_exclude_field(cls, field_definition: FieldDefinition, config: DTOConfig, dto_for: ForType) -> bool:
        """Returns ``True`` where a field should be excluded from data transfer.

        Args:
            field_definition: defined DTO field
            config: DTO configuration
            dto_for: indicates whether the DTO is for the request body or response.

        Returns:
            ``True`` if the field should not be included in any data transfer.
        """
        field_name = field_definition.name
        dto_field = field_definition.dto_field
        excluded = field_name in config.exclude
        not_included = config.include and field_name not in config.include
        private = dto_field and dto_field.mark is Mark.PRIVATE
        read_only_for_write = dto_for == "data" and dto_field and dto_field.mark is Mark.READ_ONLY
        return bool(excluded or not_included or private or read_only_for_write)

    @classmethod
    def on_registration(cls, route_handler: BaseRouteHandler, dto_for: ForType) -> None:
        """Do something each time the DTO type is encountered during signature modelling.

        Args:
            route_handler: :class:`HTTPRouteHandler <.handlers.HTTPRouteHandler>` DTO type is declared upon.
            dto_for: indicates whether the DTO is for the request body or response.
        """

        parsed_signature = route_handler.parsed_fn_signature
        if dto_for == "data":
            parsed_type = parsed_signature.parameters["data"].parsed_type
        else:
            parsed_type = parsed_signature.return_type

        if parsed_type.is_subclass_of(AbstractDTOFactory):
            raise InvalidAnnotation("AbstractDTOFactory does not support being set as a handler annotation")

        if parsed_type.is_collection:
            if len(parsed_type.inner_types) != 1:
                raise InvalidAnnotation("AbstractDTOFactory only supports homogeneous collection types")
            handler_type = parsed_type.inner_types[0]
        else:
            handler_type = parsed_type

        if not handler_type.is_subclass_of(cls.model_type):
            raise InvalidAnnotation(f"DTO narrowed with '{cls.model_type}', handler type is '{parsed_type.annotation}'")

        for config in cls.configs:
            key = (parsed_type, config)
            backend = cls._type_config_backend_map.get(key)
            if backend is None:
                backend = cls._type_config_backend_map.setdefault(
                    key,
                    MsgspecDTOBackend.from_field_definitions(
                        parsed_type, cls.parse_model(cls.model_type, config, dto_for)
                    ),
                )

            cls._handler_config_backend_map[(dto_for, route_handler, config)] = backend

    @classmethod
    def get_backend(cls, dto_for: ForType, route_handler: BaseRouteHandler) -> AbstractDTOBackend:
        """Get the DTO configuration for the given connection.

        Args:
            dto_for: indicates whether the DTO is for the request body or response.
            route_handler: Route handler instance.

        Returns:
            The DTO configuration for the connection.
        """
        config = cls.configs[0]
        return cls._handler_config_backend_map[(dto_for, route_handler, config)]

    @classmethod
    def create_openapi_schema(
        cls,
        schema_type: Literal["body", "response"],
        handler: BaseRouteHandler,
        generate_examples: bool,
        schemas: dict[str, Schema],
    ) -> Reference | Schema:
        """Create an OpenAPI request body.

        Returns:
            OpenAPI request body.
        """
        purpose = Purpose.WRITE if schema_type == "body" else Purpose.READ
        backend = cls.get_backend(purpose, handler)
        return backend.create_openapi_schema(generate_examples, schemas)
