from __future__ import annotations

import typing
from abc import abstractmethod
from inspect import getmodule
from typing import TYPE_CHECKING, Collection, Generic, TypeVar

from typing_extensions import get_type_hints

from litestar.dto._backend import DTOBackend
from litestar.dto.config import DTOConfig
from litestar.dto.data_structures import DTOData
from litestar.dto.interface import ConnectionContext, DTOInterface
from litestar.dto.types import RenameStrategy
from litestar.enums import RequestEncodingType
from litestar.exceptions.dto_exceptions import InvalidAnnotationException
from litestar.types.builtin_types import NoneType
from litestar.types.composite_types import TypeEncodersMap
from litestar.typing import FieldDefinition
from litestar.utils import find_index

if TYPE_CHECKING:
    from typing import Any, ClassVar, Generator

    from typing_extensions import Self

    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.dto.data_structures import DTOFieldDefinition
    from litestar.dto.interface import HandlerContext
    from litestar.dto.types import ForType
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("AbstractDTOFactory",)

T = TypeVar("T")


class AbstractDTOFactory(DTOInterface, Generic[T]):
    """Base class for DTO types."""

    __slots__ = ()

    config: ClassVar[DTOConfig]
    """Config objects to define properties of the DTO."""
    model_type: ClassVar[type[Any]]
    """If ``annotation`` is an iterable, this is the inner type, otherwise will be the same as ``annotation``."""

    _dto_backends: ClassVar[dict[str, DTOBackend]] = {}

    def __init__(self, connection_context: ConnectionContext) -> None:
        """Create an AbstractDTOFactory type.

        Args:
            connection_context: A :class:`ConnectionContext <.ConnectionContext>` instance, which provides
                information about the connection.
        """
        super().__init__(connection_context=connection_context)

    def __class_getitem__(cls, annotation: Any) -> type[Self]:
        field_definition = FieldDefinition.from_annotation(annotation)

        if (field_definition.is_optional and len(field_definition.args) > 2) or (
            field_definition.is_union and not field_definition.is_optional
        ):
            raise InvalidAnnotationException(
                "Unions are currently not supported as type argument to DTO. Want this? Open an issue."
            )

        if field_definition.is_forward_ref:
            raise InvalidAnnotationException("Forward references are not supported as type argument to DTO")

        # if a configuration is not provided, and the type narrowing is a type var, we don't want to create a subclass
        config = cls.get_dto_config_from_annotated_type(field_definition)

        if not config:
            if field_definition.is_type_var:
                return cls
            config = cls.config if hasattr(cls, "config") else DTOConfig()

        cls_dict: dict[str, Any] = {"config": config, "_type_backend_map": {}, "_handler_backend_map": {}}
        if not field_definition.is_type_var:
            cls_dict.update(model_type=field_definition.annotation)

        return type(f"{cls.__name__}[{annotation}]", (cls,), cls_dict)

    def builtins_to_data_type(self, builtins: Any) -> Any:
        """Coerce the unstructured data into the data type."""
        backend = self.get_backend(for_type="data", handler_id=self.connection_context.handler_id)
        return backend.populate_data_from_builtins(builtins, self.connection_context)

    def bytes_to_data_type(self, raw: bytes) -> Any:
        """Return the data held by the DTO."""
        backend = self.get_backend(for_type="data", handler_id=self.connection_context.handler_id)
        return backend.populate_data_from_raw(raw, self.connection_context)

    def data_to_encodable_type(self, data: T | Collection[T]) -> LitestarEncodableType:
        backend = self.get_backend(for_type="return", handler_id=self.connection_context.handler_id)
        return backend.encode_data(data)

    @classmethod
    @abstractmethod
    def generate_field_definitions(cls, model_type: type[Any]) -> Generator[DTOFieldDefinition, None, None]:
        """Generate ``FieldDefinition`` instances from ``model_type``.

        Yields:
            ``FieldDefinition`` instances.
        """

    @classmethod
    @abstractmethod
    def detect_nested_field(cls, field_definition: FieldDefinition) -> bool:
        """Return ``True`` if ``field_definition`` represents a nested model field.

        Args:
            field_definition: inspect type to determine if field represents a nested model.

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
        field_definition = handler_context.field_definition
        model_type_field_definition = cls.resolve_model_type(field_definition=field_definition)
        wrapper_attribute_name: str | None = None

        if not model_type_field_definition.is_subclass_of(cls.model_type):
            if resolved_generic_result := cls.resolve_generic_wrapper_type(model_type_field_definition, cls.model_type):
                model_type_field_definition, field_definition, wrapper_attribute_name = resolved_generic_result
            else:
                raise InvalidAnnotationException(
                    f"DTO narrowed with '{cls.model_type}', handler type is '{field_definition.annotation}'"
                )

        key = f"{handler_context.dto_for}::{handler_context.handler_id}"
        if key not in cls._dto_backends:
            cls._dto_backends[key] = DTOBackend(
                dto_factory=cls,
                field_definition=field_definition,
                model_type=model_type_field_definition.annotation,
                wrapper_attribute_name=wrapper_attribute_name,
                is_data_field=handler_context.dto_for == "data",
                handler_id=handler_context.handler_id,
            )

    @classmethod
    def create_openapi_schema(
        cls, dto_for: ForType, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        """Create an OpenAPI request body.

        Returns:
            OpenAPI request body.
        """
        return cls.get_backend(for_type=dto_for, handler_id=handler_id).create_openapi_schema(schema_creator)

    @classmethod
    def get_backend(cls, for_type: ForType, handler_id: str) -> DTOBackend:
        key = f"{for_type}::{handler_id}"
        return cls._dto_backends[key]

    @classmethod
    def resolve_generic_wrapper_type(
        cls, field_definition: FieldDefinition, dto_specialized_type: type[Any]
    ) -> tuple[FieldDefinition, FieldDefinition, str] | None:
        """Handle where DTO supported data is wrapped in a generic container type.

        Args:
            field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.
            dto_specialized_type: The type used to specialize the DTO.

        Returns:
            The data model type.
        """
        if (origin := field_definition.origin) and (parameters := getattr(origin, "__parameters__", None)):
            param_index = find_index(
                field_definition.inner_types, lambda x: cls.resolve_model_type(x).is_subclass_of(dto_specialized_type)
            )

            if param_index == -1:
                return None

            inner_type = field_definition.inner_types[param_index]
            model_type = cls.resolve_model_type(inner_type)
            type_var = parameters[param_index]

            for attr, attr_type in cls.get_model_type_hints(origin).items():
                if attr_type.annotation is type_var or any(t.annotation is type_var for t in attr_type.inner_types):
                    if attr_type.is_non_string_collection:
                        # the inner type of the collection type is the type var, so we need to specialize the
                        # collection type with the DTO supported type.
                        specialized_annotation = attr_type.safe_generic_origin[model_type.annotation]
                        return model_type, FieldDefinition.from_annotation(specialized_annotation), attr
                    return model_type, inner_type, attr

        return None

    @staticmethod
    def get_model_type_hints(
        model_type: type[Any], namespace: dict[str, Any] | None = None
    ) -> dict[str, FieldDefinition]:
        """Retrieve type annotations for ``model_type``.

        Args:
            model_type: Any type-annotated class.
            namespace: Optional namespace to use for resolving type hints.

        Returns:
            Parsed type hints for ``model_type`` resolved within the scope of its module.
        """
        namespace = namespace or {}
        namespace.update(vars(typing))
        namespace.update(
            {
                "TypeEncodersMap": TypeEncodersMap,
                "DTOConfig": DTOConfig,
                "RenameStrategy": RenameStrategy,
                "RequestEncodingType": RequestEncodingType,
            }
        )

        if model_module := getmodule(model_type):
            namespace.update(vars(model_module))

        return {
            k: FieldDefinition.from_kwarg(annotation=v, name=k)
            for k, v in get_type_hints(model_type, localns=namespace, include_extras=True).items()
        }

    @staticmethod
    def get_dto_config_from_annotated_type(field_definition: FieldDefinition) -> DTOConfig | None:
        """Extract data type and config instances from ``Annotated`` annotation.

        Args:
            field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.

        Returns:
            The type and config object extracted from the annotation.
        """
        if configs := [item for item in field_definition.metadata if isinstance(item, DTOConfig)]:
            return configs[0]
        return None

    @classmethod
    def resolve_model_type(cls, field_definition: FieldDefinition) -> FieldDefinition:
        """Resolve the data model type from a parsed type.

        Args:
            field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.

        Returns:
            A :class:`FieldDefinition <.typing.FieldDefinition>` that represents the data model type.
        """
        if field_definition.is_optional:
            return cls.resolve_model_type(
                next(t for t in field_definition.inner_types if not t.is_subclass_of(NoneType))
            )

        if field_definition.is_subclass_of(DTOData):
            return cls.resolve_model_type(field_definition.inner_types[0])

        if field_definition.is_collection:
            if field_definition.is_mapping:
                return cls.resolve_model_type(field_definition.inner_types[1])

            if field_definition.is_tuple:
                if any(t is Ellipsis for t in field_definition.args):
                    return cls.resolve_model_type(field_definition.inner_types[0])
            elif field_definition.is_non_string_collection:
                return cls.resolve_model_type(field_definition.inner_types[0])

        return field_definition
