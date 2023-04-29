from __future__ import annotations

from abc import ABCMeta, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from litestar.dto.interface import ConnectionContext, DTOInterface
from litestar.enums import RequestEncodingType
from litestar.types.builtin_types import NoneType
from litestar.utils.signature import ParsedType

from ._backends import MsgspecDTOBackend, PydanticDTOBackend
from ._backends.abc import BackendContext
from .config import DTOConfig
from .exc import InvalidAnnotation
from .field import Mark
from .types import FieldDefinition, FieldDefinitionsType, NestedFieldDefinition
from .utils import RenameStrategies, parse_configs_from_annotation

if TYPE_CHECKING:
    from typing import AbstractSet, Any, ClassVar, Collection, Generator

    from typing_extensions import Self

    from litestar.dto.factory.types import RenameStrategy
    from litestar.dto.interface import HandlerContext
    from litestar.dto.types import ForType
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType

    from ._backends import AbstractDTOBackend

__all__ = ["AbstractDTOFactory"]

DataT = TypeVar("DataT")


class AbstractDTOFactory(DTOInterface, Generic[DataT], metaclass=ABCMeta):
    """Base class for DTO types."""

    __slots__ = ("connection_context",)

    config: ClassVar[DTOConfig]
    """Config objects to define properties of the DTO."""
    model_type: ClassVar[type[Any]]
    """If ``annotation`` is an iterable, this is the inner type, otherwise will be the same as ``annotation``."""

    _reverse_field_mappings: ClassVar[dict[str, FieldDefinition]]
    _type_backend_map: ClassVar[dict[tuple[ForType, ParsedType, RequestEncodingType | str | None], AbstractDTOBackend]]
    _handler_backend_map: ClassVar[dict[tuple[ForType, str], AbstractDTOBackend]]

    def __init__(self, connection_context: ConnectionContext) -> None:
        """Create an AbstractDTOFactory type.

        Args:
            connection_context: A :class:`ConnectionContext <.ConnectionContext>` instance, which provides
                information about the connection.
        """
        self.connection_context = connection_context

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

        # if a configuration is not provided, and the type narrowing is a type var, we don't want to create a subclass
        configs = parse_configs_from_annotation(parsed_type)
        if parsed_type.is_type_var and not configs:
            return cls

        if configs:
            # provided config is always preferred
            config = configs[0]
        elif hasattr(cls, "config"):
            # if no config is provided, but the class has one assigned, use that
            config = cls.config
        else:
            # otherwise, create a new config
            config = DTOConfig()

        cls_dict: dict[str, Any] = {
            "config": config,
            "_reverse_field_mappings": {},
            "_type_backend_map": {},
            "_handler_backend_map": {},
        }
        if not parsed_type.is_type_var:
            cls_dict.update(model_type=parsed_type.annotation)

        return type(f"{cls.__name__}[{annotation}]", (cls,), cls_dict)

    def builtins_to_data_type(self, builtins: Any) -> Any:
        """Coerce the unstructured data into the data type."""
        backend = self._handler_backend_map[("data", self.connection_context.handler_id)]
        return backend.populate_data_from_builtins(builtins)

    def bytes_to_data_type(self, raw: bytes) -> Any:
        """Return the data held by the DTO."""
        backend = self._handler_backend_map[("data", self.connection_context.handler_id)]
        return backend.populate_data_from_raw(raw, self.connection_context)

    def data_to_encodable_type(self, data: DataT | Collection[DataT]) -> LitestarEncodableType:
        backend = self._handler_backend_map[("return", self.connection_context.handler_id)]
        return backend.encode_data(data, self.connection_context)

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
    def on_registration(cls, handler_context: HandlerContext) -> None:
        """Called each time the DTO type is encountered during signature modelling.

        Args:
            handler_context: A :class:`HandlerContext <.HandlerContext>` instance. Provides information about the
                handler and application of the DTO.
        """
        if handler_context.parsed_type.is_collection:
            if len(handler_context.parsed_type.inner_types) != 1:
                raise InvalidAnnotation("AbstractDTOFactory only supports homogeneous collection types")
            handler_type = handler_context.parsed_type.inner_types[0]
        else:
            handler_type = handler_context.parsed_type

        if not handler_type.is_subclass_of(cls.model_type):
            raise InvalidAnnotation(
                f"DTO narrowed with '{cls.model_type}', handler type is '{handler_context.parsed_type.annotation}'"
            )

        key = (handler_context.dto_for, handler_context.parsed_type, handler_context.request_encoding_type)
        backend = cls._type_backend_map.get(key)
        if backend is None:
            backend_type: type[AbstractDTOBackend]
            if handler_context.request_encoding_type in {
                RequestEncodingType.URL_ENCODED,
                RequestEncodingType.MULTI_PART,
            }:
                backend_type = PydanticDTOBackend
            else:
                backend_type = MsgspecDTOBackend

            backend_context = BackendContext(
                handler_context.parsed_type,
                _parse_model(
                    dto_factory_type=cls,
                    model_type=handler_type.annotation,
                    dto_for=handler_context.dto_for,
                    exclude=cls.config.exclude,
                    rename_fields=cls.config.rename_fields,
                    rename_strategy=cls.config.rename_strategy,
                    max_nested_depth=cls.config.max_nested_depth,
                ),
                handler_type.annotation,
            )
            backend = cls._type_backend_map.setdefault(key, backend_type(backend_context))
        cls._handler_backend_map[(handler_context.dto_for, handler_context.handler_id)] = backend

    @classmethod
    def create_openapi_schema(
        cls,
        dto_for: ForType,
        handler_id: str,
        generate_examples: bool,
        schemas: dict[str, Schema],
    ) -> Reference | Schema:
        """Create an OpenAPI request body.

        Returns:
            OpenAPI request body.
        """
        backend = cls._handler_backend_map[(dto_for, handler_id)]
        return backend.create_openapi_schema(generate_examples, schemas)


def _parse_model(
    dto_factory_type: type[AbstractDTOFactory],
    model_type: Any,
    dto_for: ForType,
    exclude: AbstractSet[str],
    rename_fields: dict[str, str],
    rename_strategy: RenameStrategy | None,
    max_nested_depth: int,
    nested_depth: int = 0,
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
    for field_definition in dto_factory_type.generate_field_definitions(model_type):
        if _should_exclude_field(field_definition, exclude, dto_for):
            continue

        if rename := rename_fields.get(field_definition.name):
            field_definition = field_definition.copy_with(serialization_name=rename)  # noqa: PLW2901
        elif rename_strategy:
            alias = RenameStrategies(rename_strategy)(field_definition.name)
            field_definition = field_definition.copy_with(serialization_name=alias)  # noqa: PLW2901

        if dto_factory_type.detect_nested_field(field_definition):
            if nested_depth == max_nested_depth:
                continue

            nested_exclude = {split[1] for s in exclude if (split := s.split(".", 1))[0] == field_definition.name}
            nested_type = _get_model_type(field_definition.annotation)
            nested = NestedFieldDefinition(
                field_definition=field_definition,
                nested_type=nested_type,
                nested_field_definitions=_parse_model(
                    dto_factory_type,
                    nested_type,
                    dto_for,
                    nested_exclude,
                    rename_fields,
                    rename_strategy,
                    max_nested_depth,
                    nested_depth + 1,
                ),
            )
            defined_fields[field_definition.name] = nested
        else:
            defined_fields[field_definition.name] = field_definition
    return defined_fields


def _should_exclude_field(field_definition: FieldDefinition, exclude: AbstractSet[str], dto_for: ForType) -> bool:
    """Returns ``True`` where a field should be excluded from data transfer.

    Args:
        field_definition: defined DTO field
        exclude: names of fields to exclude
        dto_for: indicates whether the DTO is for the request body or response.

    Returns:
        ``True`` if the field should not be included in any data transfer.
    """
    field_name = field_definition.name
    dto_field = field_definition.dto_field
    excluded = field_name in exclude
    private = dto_field and dto_field.mark is Mark.PRIVATE
    read_only_for_write = dto_for == "data" and dto_field and dto_field.mark is Mark.READ_ONLY
    return bool(excluded or private or read_only_for_write)


def _get_model_type(annotation: type) -> Any:
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
