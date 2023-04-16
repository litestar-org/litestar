from __future__ import annotations

from abc import ABCMeta, abstractmethod
from collections.abc import Collection as CollectionsCollection
from itertools import chain
from typing import TYPE_CHECKING, Generic, TypeVar

from msgspec import Struct

from litestar.dto.interface import DTOInterface
from litestar.types.builtin_types import NoneType
from litestar.utils.signature import ParsedType

from .backends import MsgspecDTOBackend
from .config import DTOConfig
from .exc import InvalidAnnotation
from .field import Mark, Purpose
from .types import FieldDefinition, FieldDefinitionsType, NestedFieldDefinition
from .utils import get_model_type_hints, parse_configs_from_annotation

if TYPE_CHECKING:
    from typing import Any, ClassVar, Collection, Generator, TypeAlias

    from typing_extensions import Self

    from litestar.connection import Request
    from litestar.enums import RequestEncodingType
    from litestar.handlers import BaseRouteHandler
    from litestar.openapi.spec import RequestBody, Schema

    from .backends import AbstractDTOBackend

__all__ = [
    "AbstractDTOFactory",
    "MsgspecBackedDTOFactory",
]

AnyRequest: TypeAlias = "Request[Any, Any, Any]"
DataT = TypeVar("DataT")
StructT = TypeVar("StructT", bound=Struct)


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
    dto_backend_type: ClassVar[type[AbstractDTOBackend]]
    """DTO backend type."""

    _reverse_field_mappings: ClassVar[dict[str, FieldDefinition]]
    _type_config_backend_map: ClassVar[dict[tuple[ParsedType, DTOConfig], AbstractDTOBackend]]
    _handler_config_backend_map: ClassVar[dict[tuple[Purpose, BaseRouteHandler, DTOConfig], AbstractDTOBackend]]

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
        cls, model_type: Any, config: DTOConfig, nested_depth: int = 0, recursive_depth: int = 0
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
            if cls.should_exclude_field(field_definition, config):
                continue

            if field_mapping := config.field_mapping.get(field_definition.name):
                if isinstance(field_mapping, str):
                    cls._reverse_field_mappings[field_mapping] = field_definition
                    field_definition = field_definition.copy_with(name=field_mapping)  # noqa: PLW2901
                else:
                    cls._reverse_field_mappings[field_mapping.name] = field_definition
                    field_definition = field_mapping  # noqa: PLW2901

            if cls.detect_nested_field(field_definition):
                nested_field_definition = cls.handle_nested(field_definition, nested_depth, recursive_depth, config)
                if nested_field_definition is not None:
                    defined_fields[field_definition.name] = nested_field_definition
                continue

            defined_fields[field_definition.name] = field_definition
        return defined_fields

    @classmethod
    def handle_nested(
        cls, field_definition: FieldDefinition, nested_depth: int, recursive_depth: int, config: DTOConfig
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
            nested.nested_type, config, nested_depth + 1, recursive_depth + is_recursive
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
    def should_exclude_field(cls, field_definition: FieldDefinition, config: DTOConfig) -> bool:
        """Returns ``True`` where a field should be excluded from data transfer.

        Args:
            field_definition: defined DTO field
            config: DTO configuration

        Returns:
            ``True`` if the field should not be included in any data transfer.
        """
        field_name = field_definition.name
        dto_field = field_definition.dto_field
        excluded = field_name in config.exclude
        not_included = config.include and field_name not in config.include
        private = dto_field and dto_field.mark is Mark.PRIVATE
        read_only_for_write = config.purpose is Purpose.WRITE and dto_field and dto_field.mark is Mark.READ_ONLY
        return bool(excluded or not_included or private or read_only_for_write)

    @classmethod
    def on_registration(cls, parsed_type: ParsedType, route_handler: BaseRouteHandler) -> None:
        """Do something each time the DTO type is encountered during signature modelling.

        Args:
            parsed_type: representing the resolved annotation of the handler function.
            route_handler: Route handler instance.
        """
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

        is_data_type = (
            "data" in route_handler.parsed_fn_signature.parameters
            and parsed_type == route_handler.parsed_fn_signature.parameters["data"].parsed_type
        )
        is_return_type = parsed_type == route_handler.parsed_fn_signature.return_type

        for config in cls.configs:
            key = (parsed_type, config)
            backend = cls._type_config_backend_map.get(key)
            if backend is None:
                backend = cls._type_config_backend_map.setdefault(
                    key,
                    cls.dto_backend_type.from_field_definitions(parsed_type, cls.parse_model(cls.model_type, config)),
                )

            if is_data_type:
                cls._handler_config_backend_map[(Purpose.WRITE, route_handler, config)] = backend

            if is_return_type:
                cls._handler_config_backend_map[(Purpose.READ, route_handler, config)] = backend

    @classmethod
    def get_backend(cls, purpose: Purpose, route_handler: BaseRouteHandler) -> AbstractDTOBackend:
        """Get the DTO configuration for the given connection.

        Args:
            purpose: Purpose of the data. ``Purpose.WRITE`` for ``"data"`` kwarg, ``Purpose.READ`` for return value.
            route_handler: Route handler instance.

        Returns:
            The DTO configuration for the connection.
        """
        config = cls.configs[0]
        return cls._handler_config_backend_map[(purpose, route_handler, config)]

    @classmethod
    def create_openapi_request_body(
        cls,
        handler: BaseRouteHandler,
        generate_examples: bool,
        media_type: RequestEncodingType | str,
        schemas: dict[str, Schema],
    ) -> RequestBody | None:
        """Create an OpenAPI request body.

        Returns:
            OpenAPI request body.
        """
        backend = cls.get_backend(Purpose.WRITE, handler)
        return backend.create_openapi_request_body(generate_examples, media_type, schemas)


class MsgspecBackedDTOFactory(AbstractDTOFactory[DataT], Generic[DataT], metaclass=ABCMeta):
    dto_backend_type = MsgspecDTOBackend

    @classmethod
    def from_bytes(cls, raw: bytes, connection: AnyRequest) -> Self:
        """Construct an instance from bytes.

        Args:
            raw: Raw connection data.
            connection: A byte representation of the DTO model.

        Returns:
            AbstractDTOFactory instance.
        """
        backend = cls.get_backend(Purpose.WRITE, connection.route_handler)
        parsed = backend.parse_raw(raw, connection.content_type[0])
        return cls(
            data=_build_data_from_struct(cls.model_type, parsed, backend.field_definitions), connection=connection
        )

    def to_encodable_type(self) -> Any:
        backend = self.get_backend(Purpose.READ, self._connection.route_handler)
        if isinstance(self._data, CollectionsCollection):
            return backend.parsed_type.origin(
                _build_struct_from_model(datum, backend.data_container_type) for datum in self._data  # pyright:ignore
            )
        return _build_struct_from_model(self._data, backend.data_container_type)


def _build_model_from_struct(model_type: type[DataT], data: Struct, field_definitions: FieldDefinitionsType) -> DataT:
    """Create instance of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    unstructured_data = {}
    for k in data.__slots__:  # type:ignore[attr-defined]
        v = getattr(data, k)

        field = field_definitions[k]

        if isinstance(field, NestedFieldDefinition) and isinstance(v, CollectionsCollection):
            parsed_type = field.field_definition.parsed_type
            if parsed_type.origin is None:  # pragma: no cover
                raise RuntimeError("Unexpected origin value for collection type.")
            unstructured_data[k] = parsed_type.origin(
                _build_model_from_struct(field.nested_type, item, field.nested_field_definitions) for item in v
            )
        elif isinstance(field, NestedFieldDefinition) and isinstance(v, Struct):
            unstructured_data[k] = _build_model_from_struct(field.nested_type, v, field.nested_field_definitions)
        else:
            unstructured_data[k] = v

    return model_type(**unstructured_data)


def _build_data_from_struct(
    model_type: type[DataT], data: Struct | Collection[Struct], field_definitions: FieldDefinitionsType
) -> DataT | Collection[DataT]:
    """Create instance or iterable of instances of ``model_type``.

    Args:
        model_type: the model type received by the DTO on type narrowing.
        data: primitive data that has been parsed and validated via the backend.
        field_definitions: model field definitions.

    Returns:
        Data parsed into ``model_type``.
    """
    if isinstance(data, CollectionsCollection):
        return type(data)(  # type:ignore[return-value]
            _build_data_from_struct(model_type, item, field_definitions) for item in data  # type:ignore[call-arg]
        )
    return _build_model_from_struct(model_type, data, field_definitions)


def _build_struct_from_model(model: Any, struct_type: type[StructT]) -> StructT:
    """Convert ``model`` to instance of ``struct_type``

    It is expected that attributes of ``struct_type`` are a subset of the attributes of ``model``.

    Args:
        model: a model instance
        struct_type: a subclass of ``msgspec.Struct``

    Returns:
        Instance of ``struct_type``.
    """
    data = {}
    for key, parsed_type in get_model_type_hints(struct_type).items():
        model_val = getattr(model, key)
        if parsed_type.is_subclass_of(Struct):
            data[key] = _build_struct_from_model(model_val, parsed_type.annotation)
        elif parsed_type.is_union:
            data[key] = _handle_union_type(parsed_type, model_val)
        elif parsed_type.is_collection:
            data[key] = _handle_collection_type(parsed_type, model_val)
        else:
            data[key] = model_val
    return struct_type(**data)


def _handle_union_type(parsed_type: ParsedType, model_val: Any) -> Any:
    """Handle union type.

    Args:
        parsed_type: Parsed type.
        model_val: Model value.

    Returns:
        Model value.
    """
    for inner_type in parsed_type.inner_types:
        if inner_type.is_subclass_of(Struct):
            # If there are multiple struct inner types, we use the first one that creates without exception.
            # This is suboptimal, and perhaps can be improved by assigning the model that the inner struct
            # was derived upon to the struct itself, which would allow us to isolate the correct struct to use
            # for the nested model type instance. For the most likely case of an optional union of a single
            # nested type, this should be sufficient.
            try:
                return _build_struct_from_model(model_val, inner_type.annotation)
            except (AttributeError, TypeError):
                continue
    return model_val


def _handle_collection_type(parsed_type: ParsedType, model_val: Any) -> Any:
    """Handle collection type.

    Args:
        parsed_type: Parsed type.
        model_val: Model value.

    Returns:
        Model value.
    """
    if parsed_type.inner_types and (inner_type := parsed_type.inner_types[0]).is_subclass_of(Struct):
        return parsed_type.origin(_build_struct_from_model(m, inner_type.annotation) for m in model_val)
    return model_val
