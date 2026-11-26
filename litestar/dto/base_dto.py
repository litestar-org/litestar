# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import dataclasses
import typing
from abc import abstractmethod
from collections.abc import Collection
from contextlib import suppress
from inspect import getmodule
from typing import TYPE_CHECKING, Generic, TypeVar, get_type_hints

import msgspec

from litestar.dto._applicability import _without_type_aliases, build_schema_annotation, resolve_dto_target
from litestar.dto._backend import DTOBackend
from litestar.dto._msgspec_rejection import qualified_name
from litestar.dto.config import DTOConfig
from litestar.dto.data_structures import DTOData
from litestar.dto.types import RenameStrategy
from litestar.enums import RequestEncodingType
from litestar.exceptions.dto_exceptions import DTOTransferTypeError, InvalidAnnotationException
from litestar.params import BodyKwarg
from litestar.types.builtin_types import NoneType
from litestar.types.composite_types import TypeEncodersMap
from litestar.typing import FieldDefinition
from litestar.utils.signature import ParsedSignature
from litestar.utils.typing import _substitute_typevars

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Generator
    from typing import Any, ClassVar, Self

    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.connection import ASGIConnection
    from litestar.dto._backend import TransferModelRegistry
    from litestar.dto.data_structures import DTOFieldDefinition
    from litestar.handlers.base import BaseRouteHandler
    from litestar.openapi.spec import Reference, Schema
    from litestar.types import TypeDecodersSequence
    from litestar.types.serialization import LitestarEncodableType

__all__ = ("AbstractDTO",)

T = TypeVar("T")


class AbstractDTO(Generic[T]):
    """Base class for DTO types."""

    __slots__ = ("asgi_connection",)

    config: ClassVar[DTOConfig]
    """Config objects to define properties of the DTO."""
    model_type: type[T]
    """If ``annotation`` is an iterable, this is the inner type, otherwise will be the same as ``annotation``."""
    attribute_accessor: Callable[[object, str], Any] = getattr
    """:func:`getattr` like callable to access attributes on the data source"""

    __schema_name__: ClassVar[None | str] = None

    def __init__(self, asgi_connection: ASGIConnection) -> None:
        """Create an AbstractDTOFactory type.

        Args:
            asgi_connection: A :class:`ASGIConnection <litestar.connection.base.ASGIConnection>` instance.
        """
        self.asgi_connection = asgi_connection

    def __class_getitem__(cls, annotation: Any) -> type[Self]:
        field_definition = FieldDefinition.from_annotation(annotation)

        if (field_definition.is_optional and len(field_definition.args) > 2) or (
            field_definition.is_union and not field_definition.is_optional
        ):
            raise InvalidAnnotationException("Unions are currently not supported as type argument to DTOs.")

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

        return type(f"{cls.__name__}[{annotation}]", (cls,), cls_dict)  # pyright: ignore[reportReturnType]

    def __init_subclass__(cls, **kwargs: Any) -> None:
        if (config := getattr(cls, "config", None)) and (model_type := getattr(cls, "model_type", None)):
            # it's a concrete class
            cls.config = cls.get_config_for_model_type(config, model_type)

    @classmethod
    def get_config_for_model_type(cls, config: DTOConfig, model_type: type[Any]) -> DTOConfig:
        """Create a new configuration for this specific ``model_type``, during the
        creation of the factory.

        The returned config object will be set as the ``config`` attribute on the newly
        defined factory class.

        .. versionadded: 2.11

        """
        return config

    def decode_builtins(self, value: dict[str, Any]) -> Any:
        """Decode a dictionary of Python values into an the DTO's datatype."""

        backend = self.asgi_connection.route_handler._dto_data_backend
        return backend.populate_data_from_builtins(value, self.asgi_connection)

    def decode_bytes(self, value: bytes) -> Any:
        """Decode a byte string into an the DTO's datatype."""

        backend = self.asgi_connection.route_handler._dto_data_backend
        return backend.populate_data_from_raw(value, self.asgi_connection)

    def data_to_encodable_type(self, data: T | Collection[T]) -> LitestarEncodableType:
        backend = self.asgi_connection.route_handler._dto_return_backend
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
    def is_supported_model_type_field(cls, field_definition: FieldDefinition) -> bool:
        """Check support for the given type.

        Args:
            field_definition: A :class:`FieldDefinition <litestar.typing.FieldDefinition>` instance.

        Returns:
            Whether the type of the field definition is supported by the DTO.
        """
        return field_definition.is_subclass_of(cls.model_type) or (
            field_definition.origin
            and any(
                cls.resolve_model_type(inner_field).is_subclass_of(cls.model_type)
                for inner_field in field_definition.inner_types
            )
        )

    @classmethod
    def create_for_annotation(cls, annotation: Any, *, type_decoders: TypeDecodersSequence | None = None) -> DTOBackend:
        """Create a DTO backend for a type annotation, to use the DTO outside a request.

        Args:
            annotation: The annotation of the data. Declared as a body, e.g. ``JSONBody[Model]``, it is data to decode
                the way a handler receives it, otherwise data to encode the way a handler returns it.
            type_decoders: Type decoders used by the backend when it parses data.

        Returns:
            The DTO backend.
        """
        return cls.create_for_field_definition(FieldDefinition.from_annotation(annotation), type_decoders=type_decoders)

    @classmethod
    def create_for_field_definition(
        cls,
        field_definition: FieldDefinition,
        handler_id: str | None = None,
        backend_cls: type[DTOBackend] | None = None,
        *,
        transfer_models: TransferModelRegistry | None = None,
        type_decoders: TypeDecodersSequence | None = None,
    ) -> DTOBackend:
        """Creates a DTO backend for a field definition.

        Args:
            field_definition: A :class:`FieldDefinition <litestar.typing.FieldDefinition>` instance. Declared as a
                body, e.g. ``JSONBody[Model]``, it is the data the handler receives, otherwise the data it returns.
            handler_id: ID of the route handler for which to create a DTO instance, if any.
            backend_cls: Alternative DTO backend class to use
            transfer_models: The transfer models of the application, shared by the backends that build the same one.
            type_decoders: Type decoders used by the backend when it parses data without a connection.

        Returns:
            The DTO backend, stored on the route handler or used on its own.
        """

        is_data_field = isinstance(field_definition.kwarg_definition, BodyKwarg)
        if (target := resolve_dto_target(cls, field_definition, is_data_field=is_data_field)) is None:
            raise InvalidAnnotationException(
                f"DTO narrowed with '{cls.model_type}', handler type is '{field_definition.annotation}'"
            )

        if backend_cls is None:
            backend_cls = DTOBackend

        backend = backend_cls(
            dto_factory=cls,
            field_definition=target.transfer_field,
            model_type=target.model_field.annotation,
            wrapper_attribute_name=target.wrapper_attribute_name,
            is_data_field=is_data_field,
            handler_id=handler_id,
            transfer_models=transfer_models,
            type_decoders=type_decoders,
        )
        backend._passes_none = target.passes_none
        return backend

    @classmethod
    def create_openapi_schema(
        cls, field_definition: FieldDefinition, route_handler: BaseRouteHandler, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        """Create an OpenAPI request body.

        Args:
            field_definition: A parsed type annotation that represents the annotation used on the handler. Declared
                as a body, e.g. ``JSONBody[Model]``, it is the data the handler receives, otherwise the data it
                returns.
            route_handler: The route handler holding the DTO backend.
            schema_creator: A factory for creating schemas. Has a ``for_field_definition()`` method that accepts a
                :class:`~litestar.typing.FieldDefinition` instance.

        Returns:
            OpenAPI request body.
        """
        is_data_field = isinstance(field_definition.kwarg_definition, BodyKwarg)
        backend: DTOBackend = route_handler._dto_data_backend if is_data_field else route_handler._dto_return_backend  # type: ignore[assignment]
        with suppress(InvalidAnnotationException):
            field_definition = _without_type_aliases(field_definition, route_handler.signature_namespace)

        try:
            return schema_creator.for_field_definition(
                FieldDefinition.from_annotation(
                    build_schema_annotation(cls, backend, field_definition),
                    kwarg_definition=field_definition.kwarg_definition,
                )
            )
        except TypeError as exc:
            from litestar.di._route_handler import HandlerErrorPrefix

            with HandlerErrorPrefix.for_handler(route_handler).wrap_dto_exception():
                try:
                    msgspec.json.Decoder(backend.annotation, strict=False)
                except TypeError as decoder_exc:
                    raise DTOTransferTypeError(
                        f"msgspec cannot describe the transfer model of {qualified_name(backend.model_type)!r}: {exc}"
                    ) from decoder_exc
            raise

    @classmethod
    def resolve_generic_wrapper_type(
        cls, field_definition: FieldDefinition
    ) -> tuple[FieldDefinition, FieldDefinition, str] | None:
        """Handle where DTO supported data is wrapped in a generic container type.

        Args:
            field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.

        Returns:
            The data model type.
        """
        parameters = getattr(field_definition.origin, "__parameters__", ())
        if len(parameters) != len(field_definition.args):
            return None
        for parameter, inner_field in zip(parameters, field_definition.inner_types, strict=True):
            model_field_definition = cls.resolve_model_type(inner_field)
            if not model_field_definition.is_subclass_of(cls.model_type):
                continue
            for attr, attr_type in cls.get_model_type_hints(field_definition.origin).items():
                if attr_type.annotation is parameter:
                    return model_field_definition, inner_field, attr
                if parameter in getattr(attr_type.annotation, "__parameters__", ()):
                    annotation = _substitute_typevars(
                        attr_type.annotation, dict(zip(parameters, field_definition.args, strict=True))
                    )
                    return model_field_definition, FieldDefinition.from_annotation(annotation), attr
            return None
        return None

    @staticmethod
    def get_model_namespace(model_type: type[Any], namespace: dict[str, Any] | None = None) -> dict[str, Any]:
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
        return namespace

    @classmethod
    def get_property_fields(cls, model_type: type[Any]) -> dict[str, FieldDefinition]:
        return {
            name: dataclasses.replace(
                ParsedSignature.from_property(
                    attr,
                    cls.get_model_namespace(model_type),
                ).return_type,
                name=name,
            )
            for name, attr in vars(model_type).items()
            if isinstance(attr, property) and attr.fget is not None
        }

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
        namespace = AbstractDTO.get_model_namespace(model_type, namespace)

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
        return next((item for item in field_definition.metadata if isinstance(item, DTOConfig)), None)

    @classmethod
    def resolve_model_type(cls, field_definition: FieldDefinition) -> FieldDefinition:
        """Resolve the data model type from a parsed type.

        Args:
            field_definition: A parsed type annotation that represents the annotation used to narrow the DTO type.

        Returns:
            A :class:`FieldDefinition <.typing.FieldDefinition>` that represents the data model type.
        """
        if field_definition.is_optional:
            non_none = [t for t in field_definition.inner_types if not t.is_subclass_of(NoneType)]
            return cls.resolve_model_type(non_none[0]) if len(non_none) == 1 else field_definition

        if not field_definition.inner_types:
            return field_definition

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
