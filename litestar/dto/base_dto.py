# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import dataclasses
import typing
import warnings
from abc import abstractmethod
from collections.abc import Collection
from inspect import getmodule
from typing import TYPE_CHECKING, Final, Generic, TypeVar, get_type_hints
from weakref import WeakSet, WeakValueDictionary

from litestar.dto._plan import build_schema_annotation, create_backend, dto_name
from litestar.dto.config import DTOConfig
from litestar.dto.data_structures import DTOData
from litestar.dto.types import RenameStrategy
from litestar.enums import RequestEncodingType
from litestar.exceptions import LitestarDeprecationWarning
from litestar.exceptions.dto_exceptions import DTOFactoryException, InvalidAnnotationException
from litestar.params import BodyKwarg
from litestar.types.builtin_types import NoneType
from litestar.types.composite_types import TypeEncodersMap
from litestar.typing import FieldDefinition
from litestar.utils.deprecation import warn_deprecation
from litestar.utils.signature import ParsedSignature

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Generator
    from typing import Any, ClassVar, Self

    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.connection import ASGIConnection
    from litestar.dto._backend import DTOBackend
    from litestar.dto.data_structures import DTOFieldDefinition
    from litestar.handlers.base import BaseRouteHandler
    from litestar.openapi.spec import Reference, Schema
    from litestar.types.serialization import LitestarEncodableType
    from litestar.utils.deprecation import DeprecatedKind

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

    _direct_backends: ClassVar[dict[str, dict[bool, DTOBackend]]]
    __schema_name__: ClassVar[None | str] = None

    def __init__(self, asgi_connection: ASGIConnection) -> None:
        """Create an AbstractDTOFactory type.

        .. deprecated:: 3.0
            A DTO is applied through the plan of its route handler and DTO classes are no longer instantiated per
            connection. Will be removed in 4.0.

        Args:
            asgi_connection: A :class:`ASGIConnection <litestar.connection.base.ASGIConnection>` instance.
        """
        _warn_deprecated_call("AbstractDTO.__init__", "method", _NO_INSTANCE_REPLACEMENT)
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

        cls_dict: dict[str, Any] = {"config": config}
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
        """Decode a dictionary of Python values into an the DTO's datatype.

        .. deprecated:: 3.0
            Will be removed in 4.0. The framework no longer calls it, nor an override of it.
        """
        _warn_deprecated_call("AbstractDTO.decode_builtins", "method", _NO_INSTANCE_REPLACEMENT)
        backend = self._connection_backend(is_data_field=True)
        return type(self)._wrap_decoder(backend.populate_data_from_builtins)(value, self.asgi_connection)

    def decode_bytes(self, value: bytes) -> Any:
        """Decode a byte string into an the DTO's datatype.

        .. deprecated:: 3.0
            Will be removed in 4.0. The framework no longer calls it, nor an override of it.
        """
        _warn_deprecated_call("AbstractDTO.decode_bytes", "method", _NO_INSTANCE_REPLACEMENT)
        backend = self._connection_backend(is_data_field=True)
        return type(self)._wrap_decoder(backend.populate_data_from_raw)(value, self.asgi_connection)

    def data_to_encodable_type(self, data: T | Collection[T]) -> LitestarEncodableType:
        """Encode data into the DTO's transfer type.

        .. deprecated:: 3.0
            Will be removed in 4.0. The framework no longer calls it, nor an override of it.
        """
        _warn_deprecated_call("AbstractDTO.data_to_encodable_type", "method", _NO_INSTANCE_REPLACEMENT)
        return self._connection_backend(is_data_field=False).encode_data(data)

    def _connection_backend(self, *, is_data_field: bool) -> DTOBackend:
        handler = self.asgi_connection.route_handler
        return _find_backend(type(self), handler, handler.handler_id, is_data_field=is_data_field)

    @classmethod
    def _wrap_decoder(
        cls, decoder: Callable[[Any, ASGIConnection[Any, Any, Any, Any]], Any]
    ) -> Callable[[Any, ASGIConnection[Any, Any, Any, Any]], Any]:
        return decoder

    @classmethod
    def _overrides(cls, name: str) -> bool:
        """Whether the class overrides the member ``name`` of :class:`AbstractDTO`."""
        attribute = getattr(cls, name)
        base = vars(AbstractDTO)[name]
        return getattr(attribute, "__func__", attribute) is not getattr(base, "__func__", base)

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
    def create_for_field_definition(
        cls,
        field_definition: FieldDefinition,
        handler_id: str,
        backend_cls: type[DTOBackend] | None = None,
    ) -> None:
        """Creates a DTO subclass for a field definition.

        .. deprecated:: 3.0
            Backends are created when a route handler is registered. Will be removed in 4.0. The framework no longer
            calls it, nor an override of it.

        Args:
            field_definition: A :class:`FieldDefinition <litestar.typing.FieldDefinition>` instance. Declared as a
                body, e.g. ``JSONBody[Model]``, it is the data the handler receives, otherwise the data it returns.
            handler_id: ID of the route handler for which to create a DTO instance.
            backend_cls: Alternative DTO backend class to use

        Returns:
            None
        """
        _warn_deprecated_call(
            "AbstractDTO.create_for_field_definition",
            "classmethod",
            "Backends are created when a route handler is registered, and handler.data_dto and handler.return_dto "
            "name the DTO classes it applies. There is no replacement for creating a backend outside registration "
            "yet.",
        )
        is_data_field = isinstance(field_definition.kwarg_definition, BodyKwarg)
        backend = create_backend(
            cls, field_definition, is_data_field=is_data_field, handler_id=handler_id, backend_cls=backend_cls
        )
        if "_direct_backends" not in vars(cls):
            cls._direct_backends = {}
        cls._direct_backends.setdefault(str(handler_id), {})[is_data_field] = backend

    @classmethod
    def create_openapi_schema(
        cls, field_definition: FieldDefinition, handler_id: str, schema_creator: SchemaCreator
    ) -> Reference | Schema:
        """Create an OpenAPI request body.

        .. deprecated:: 3.0
            Will be removed in 4.0. The framework no longer calls it, nor an override of it. Calling it does not
            emit a deprecation warning, because plugins call it and there is no replacement yet.

        Args:
            field_definition: A parsed type annotation that represents the annotation used on the handler. Declared
                as a body, e.g. ``JSONBody[Model]``, it is the data the handler receives, otherwise the data it
                returns.
            handler_id: ID of the route handler for which to create a DTO instance.
            schema_creator: A factory for creating schemas. Has a ``for_field_definition()`` method that accepts a
                :class:`~litestar.typing.FieldDefinition` instance.

        Returns:
            OpenAPI request body.
        """
        handler = _registered_handlers.get(handler_id)
        is_data_field = isinstance(field_definition.kwarg_definition, BodyKwarg) or (
            handler is not None and field_definition is handler.parsed_data_field
        )
        backend = _find_backend(cls, handler, handler_id, is_data_field=is_data_field)
        return schema_creator.for_field_definition(
            FieldDefinition.from_annotation(
                build_schema_annotation(cls, backend, field_definition),
                kwarg_definition=field_definition.kwarg_definition,
            )
        )

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
        if field_definition.origin and (
            inner_fields := [
                inner_field
                for inner_field in field_definition.inner_types
                if cls.resolve_model_type(inner_field).is_subclass_of(cls.model_type)
            ]
        ):
            inner_field = inner_fields[0]
            model_field_definition = cls.resolve_model_type(inner_field)

            for attr, attr_type in cls.get_model_type_hints(field_definition.origin).items():
                if isinstance(attr_type.annotation, TypeVar) or any(
                    isinstance(t.annotation, TypeVar) for t in attr_type.inner_types
                ):
                    if attr_type.is_non_string_collection:
                        # the inner type of the collection type is the type var, so we need to specialize the
                        # collection type with the DTO supported type.
                        specialized_annotation = attr_type.safe_generic_origin[model_field_definition.annotation]
                        return model_field_definition, FieldDefinition.from_annotation(specialized_annotation), attr
                    return model_field_definition, inner_field, attr
        return None

    @staticmethod
    def get_model_namespace(model_type: type[Any], namespace: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build the namespace the type hints of ``model_type`` are resolved in.

        Args:
            model_type: The model whose type hints are resolved.
            namespace: Names to start from; a non-empty mapping is updated in place.

        Returns:
            The names of :mod:`typing`, the DTO configuration types and the module of ``model_type``, added to
            ``namespace``.
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
        return namespace

    @classmethod
    def get_property_fields(cls, model_type: type[Any]) -> dict[str, FieldDefinition]:
        """Return a field definition for each property of ``model_type``.

        Args:
            model_type: The model whose properties are read, without those of its base classes.

        Returns:
            The field definitions keyed by property name, typed with the return annotation of the getter.
        """
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


def _find_backend(
    dto: type[AbstractDTO[Any]], handler: BaseRouteHandler | None, handler_id: str, *, is_data_field: bool
) -> DTOBackend:
    """Return the backend ``handler`` applies in the direction: the one in its plan, else the one a direct call of
    :meth:`AbstractDTO.create_for_field_definition` on ``dto`` stored for ``handler_id``.
    """
    if handler is not None and (plan := handler._dto_plan) is not None:
        direction_plan = plan.data if is_data_field else plan.return_
        if direction_plan is not None:
            return direction_plan.backend
    direct_backends: dict[str, dict[bool, DTOBackend]] = vars(dto).get("_direct_backends", {})
    if (backend := direct_backends.get(str(handler_id), {}).get(is_data_field)) is not None:
        return backend
    raise DTOFactoryException(
        f"Handler {str(handler or handler_id)!r} has no {'data' if is_data_field else 'return'} DTO, and no backend "
        f"of {dto_name(dto)} was created for it"
    )


_registered_handlers: WeakValueDictionary[str, BaseRouteHandler] = WeakValueDictionary()


_DEPRECATED_ENTRY_POINTS: Final = (
    "create_for_field_definition",
    "decode_bytes",
    "decode_builtins",
    "data_to_encodable_type",
    "create_openapi_schema",
)
_warned_dto_classes: WeakSet[type[AbstractDTO[Any]]] = WeakSet()


def register_handler_id(handler: BaseRouteHandler) -> None:
    """Make ``handler`` findable by its ``handler_id`` for the deprecated direct calls, as long as it is alive, and
    warn once for each DTO class of its plan that overrides a deprecated entry point.
    """
    _registered_handlers[handler.handler_id] = handler
    if (plan := handler._dto_plan) is not None:
        for dto in (plan.data_dto, plan.return_.dto if plan.return_ else None):
            if dto is not None and dto not in _warned_dto_classes:
                _warned_dto_classes.add(dto)
                _warn_overridden_entry_points(dto)


def _warn_overridden_entry_points(dto: type[AbstractDTO[Any]]) -> None:
    for name in _DEPRECATED_ENTRY_POINTS:
        if getattr(getattr(dto, name), "__func__", getattr(dto, name)) is not _base_function(name):
            warnings.warn(
                f"{dto_name(dto)} overrides AbstractDTO.{name}, which is deprecated since litestar 3.0 and no longer "
                "called: the override has no effect. The method will be removed in 4.0.",
                LitestarDeprecationWarning,
                stacklevel=4,
            )


def _base_function(name: str) -> Any:
    member = vars(AbstractDTO)[name]
    return getattr(member, "__func__", member)


_NO_INSTANCE_REPLACEMENT: Final = (
    "A route handler applies its DTOs through the plan built when it is registered, and handler.data_dto and "
    "handler.return_dto name the DTO classes it applies. There is no replacement for decoding or encoding with a "
    "DTO outside a route handler yet."
)


def _warn_deprecated_call(name: str, kind: DeprecatedKind, info: str) -> None:
    warn_deprecation("3.0", name, kind, removal_in="4.0", info=info, stacklevel=4)
