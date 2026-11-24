from __future__ import annotations

import dataclasses
from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from contextvars import ContextVar
from dataclasses import dataclass
from types import NoneType
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

import msgspec

from litestar._layers.errors import HandlerErrorPrefix
from litestar.di._helpers import _format_key
from litestar.dto._backend import DTOBackend, _qualified_name
from litestar.dto._registry import TransferModelNaming, TransferModelRegistry, handler_name_scope
from litestar.dto.data_structures import DTOData
from litestar.enums import RequestEncodingType
from litestar.exceptions.dto_exceptions import (
    DTOFactoryException,
    DTONotApplicableError,
    DTOTransferTypeError,
    InvalidAnnotationException,
    MissingDTOError,
)
from litestar.params import BodyKwarg
from litestar.response.base import Response
from litestar.types import Empty
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from collections.abc import Callable, Hashable

    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.app import Litestar
    from litestar.connection import ASGIConnection
    from litestar.dto.base_dto import AbstractDTO
    from litestar.handlers.base import BaseRouteHandler
    from litestar.openapi.spec import Reference, Schema
    from litestar.plugins import SerializationPlugin
    from litestar.types.empty import EmptyType
    from litestar.types.serialization import LitestarEncodableType

__all__ = (
    "DTODeclaration",
    "DTODirectionPlan",
    "DTOPlan",
    "DTOTarget",
    "DecodeFn",
    "EncodeFn",
    "build_dto_plan",
    "build_schema_annotation",
    "create_backend",
    "create_dto_openapi_schema",
    "dto_name",
    "read_dto_declaration",
    "resolve_dto_target",
    "take_plan_build",
)

DecodeFn: TypeAlias = "Callable[[Any, ASGIConnection[Any, Any, Any, Any]], Any]"
EncodeFn: TypeAlias = "Callable[[Any, ASGIConnection[Any, Any, Any, Any]], LitestarEncodableType]"


@dataclass(frozen=True, slots=True)
class DTODirectionPlan:
    """How a route handler applies a DTO in one direction, to the data it receives or to the data it returns."""

    dto: type[AbstractDTO[Any]]
    """The DTO class applied in this direction"""
    backend: DTOBackend
    """The backend built for the handler's own field in this direction, bound to the handler's type decoders"""
    schema_annotation: Any
    """The annotation the field is documented with in the OpenAPI schema"""


@dataclass(frozen=True, slots=True)
class DTOPlan:
    """How a route handler applies its DTOs. Built once by :func:`build_dto_plan` when the handler is registered,
    stored on the handler and never modified.
    """

    data: DTODirectionPlan | None
    """The DTO applied to the data the handler receives. ``None`` if no DTO applies to it, or if the handler
    receives no data
    """
    return_: DTODirectionPlan | None
    """The DTO applied to the data the handler returns. ``None`` if no DTO applies to it"""
    data_dto: type[AbstractDTO[Any]] | None
    """The resolved data DTO class. It may be set while :attr:`data` is ``None``, for a handler configured with a
    ``dto`` that receives no data
    """
    decode_bytes: DecodeFn | None
    """Decode raw request data with the data DTO. Set exactly when :attr:`data` is set"""
    decode_builtins: DecodeFn | None
    """Decode builtin values, such as form data, with the data DTO. Set exactly when :attr:`data` is set"""
    encode: EncodeFn | None
    """Encode returned data with the return DTO. Set exactly when :attr:`return_` is set"""


@dataclass(frozen=True, slots=True)
class DTODeclaration:
    """A route handler's declaration of one of its DTO options, and where it comes from."""

    option: Literal["dto", "return_dto"]
    """The option declared"""
    value: type[AbstractDTO[Any]] | None | EmptyType
    """The declared value, ``Empty`` if neither the handler nor a layer above it declares the option"""
    source: Literal["handler", "layer"] | None
    """``"handler"`` if the handler declares the option itself, ``"layer"`` if a layer above it does, ``None`` if
    :attr:`value` is ``Empty``
    """


def read_dto_declaration(handler: BaseRouteHandler, option: Literal["dto", "return_dto"]) -> DTODeclaration:
    """Return the declaration of ``option`` for ``handler``: its own value if it declares one, otherwise the value
    of the closest layer above it that declares one.
    """
    own, inherited = (
        (handler._dto, handler._inherited_dto)
        if option == "dto"
        else (handler._return_dto, handler._inherited_return_dto)
    )
    if own is not Empty:
        return DTODeclaration(option=option, value=own, source="handler")
    if inherited is not Empty:
        return DTODeclaration(option=option, value=inherited, source="layer")
    return DTODeclaration(option=option, value=Empty, source=None)


@dataclass(frozen=True, slots=True)
class DTOTarget:
    """What a DTO applies to in an annotation it can handle, see :func:`resolve_dto_target`."""

    model_field: FieldDefinition
    """The model type the DTO transfers"""
    transfer_field: FieldDefinition
    """The annotation the backend is built for: the whole annotation, or the wrapped one for a generic wrapper"""
    wrapper_attribute_name: str | None
    """The attribute of the generic wrapper holding the data, ``None`` without a wrapper"""
    passes_none: bool
    """Whether the whole value may be ``None``"""
    wrapped_passes_none: bool
    """Whether the value of the wrapper attribute may be ``None``. ``False`` without a wrapper"""


_FORM_MEDIA_TYPES = (RequestEncodingType.URL_ENCODED, RequestEncodingType.MULTI_PART)
_STREAM_ORIGINS = (AsyncGenerator, AsyncIterator, Generator, Iterator)


def _without_optional(field_definition: FieldDefinition | None) -> FieldDefinition | None:
    if field_definition is None:
        return None
    annotation = field_definition.annotation
    if annotation is Empty or annotation is None or annotation is NoneType:
        return None
    if field_definition.is_optional:
        return next(inner for inner in field_definition.inner_types if not inner.is_subclass_of(NoneType))
    return field_definition


def _is_form_body(field_definition: FieldDefinition) -> bool:
    kwarg_definition = field_definition.kwarg_definition
    return isinstance(kwarg_definition, BodyKwarg) and kwarg_definition.media_type in _FORM_MEDIA_TYPES


def _is_form_collection(field_definition: FieldDefinition, inner: FieldDefinition) -> bool:
    data = inner.inner_types[0] if inner.is_subclass_of(DTOData) else inner
    return _is_form_body(field_definition) and data.is_collection


def resolve_dto_target(
    dto: type[AbstractDTO[Any]],
    field_definition: FieldDefinition | None,
    direction: Literal["data", "return"],
) -> DTOTarget | None:
    """Return what ``dto`` applies to in ``field_definition``, the data a handler receives or returns depending on
    ``direction``, or ``None`` if it cannot be applied to it.

    The DTO applies to an annotation without ``None``, or to the first member of an optional annotation that is not
    ``None``, whose model type, unwrapped from ``DTOData``, a collection, a mapping value or a variadic tuple, is a
    subclass of the DTO's model type, except for a collection or mapping on a form body. In the return direction
    the DTO must also support that annotation, and it applies to a model wrapped in a generic type.
    """
    return _resolve_target(dto, field_definition, direction, check_support=True)


def _resolve_target(
    dto: type[AbstractDTO[Any]],
    field_definition: FieldDefinition | None,
    direction: Literal["data", "return"],
    *,
    check_support: bool,
) -> DTOTarget | None:
    if (inner := _without_optional(field_definition)) is None or field_definition is None:
        return None
    if check_support and direction == "return" and not dto.is_supported_model_type_field(inner):
        return None

    passes_none = field_definition.is_optional
    model_field = dto.resolve_model_type(inner)
    if model_field.is_subclass_of(dto.model_type):  # pyright: ignore[reportGeneralTypeIssues]
        if direction == "data" and model_field is not inner and _is_form_collection(field_definition, inner):
            return None
        return DTOTarget(
            model_field=model_field,
            transfer_field=field_definition,
            wrapper_attribute_name=None,
            passes_none=passes_none,
            wrapped_passes_none=False,
        )

    if (
        direction == "return"
        and model_field is inner
        and not inner.is_union
        and (wrapped := dto.resolve_generic_wrapper_type(inner))
    ):
        model_field, transfer_field, wrapper_attribute_name = wrapped
        return DTOTarget(
            model_field=model_field,
            transfer_field=transfer_field,
            wrapper_attribute_name=wrapper_attribute_name,
            passes_none=passes_none,
            wrapped_passes_none=transfer_field.is_optional,
        )
    return None


def create_backend(
    dto: type[AbstractDTO[Any]],
    field_definition: FieldDefinition,
    *,
    is_data_field: bool,
    handler_id: str,
    backend_cls: type[DTOBackend] | None = None,
    registry: TransferModelRegistry | None = None,
    name_scope: Hashable | None = None,
    target: DTOTarget | None = None,
) -> DTOBackend:
    """Create the backend of ``dto`` for ``field_definition``, the data a handler receives if ``is_data_field``,
    otherwise the data it returns. Every backend of a plan is created here.

    The backend names its transfer models in ``registry`` under ``name_scope``, which are given together; without
    them it names them in a registry of its own. It is built for ``target``, or, without one, for what
    :func:`resolve_dto_target` resolves.

    Raises:
        InvalidAnnotationException: If ``dto`` cannot be applied to ``field_definition``
        TypeError: If only one of ``registry`` and ``name_scope`` is given
    """
    if (registry is None) != (name_scope is None):
        raise TypeError("create_backend() takes both 'registry' and 'name_scope', or neither")

    if target is None:
        target = resolve_dto_target(dto, field_definition, "data" if is_data_field else "return")
        if target is None:
            raise InvalidAnnotationException(
                f"DTO narrowed with '{dto.model_type}', handler type is '{field_definition.annotation}'"  # pyright: ignore[reportGeneralTypeIssues]
            )

    if backend_cls is None:
        backend_cls = DTOBackend

    backend = backend_cls.__new__(backend_cls)
    if registry is not None:
        backend._naming = TransferModelNaming(registry, name_scope)
    backend._passes_none = target.passes_none
    backend._wrapped_passes_none = target.wrapped_passes_none
    backend_cls.__init__(
        backend,
        dto_factory=dto,
        field_definition=target.transfer_field,
        model_type=target.model_field.annotation,
        wrapper_attribute_name=target.wrapper_attribute_name,
        is_data_field=is_data_field,
        handler_id=handler_id,
    )
    return backend


def build_schema_annotation(dto: type[AbstractDTO[Any]], backend: DTOBackend, field_definition: FieldDefinition) -> Any:
    """Return the annotation to document ``field_definition`` with: the backend's annotation, or, for a model
    wrapped in a generic type other than a ``Response``, the outer generic type with the model replaced by the
    transfer model.
    """
    if backend.wrapper_attribute_name and not field_definition.is_subclass_of(Response):
        model_type = dto.model_type  # pyright: ignore[reportGeneralTypeIssues]
        generic_args = tuple(backend.transfer_model_type if arg is model_type else arg for arg in field_definition.args)
        return field_definition.safe_generic_origin[generic_args]
    return backend.annotation


@dataclass(slots=True)
class _PlanBuild:
    dto: type[AbstractDTO[Any]]
    is_data_field: bool
    backend: DTOBackend | None = None
    registry: TransferModelRegistry | None = None
    name_scope: Hashable | None = None


_plan_build: ContextVar[_PlanBuild | None] = ContextVar("_plan_build", default=None)


def take_plan_build(dto: type[AbstractDTO[Any]]) -> _PlanBuild | None:
    """Return the plan build in progress for ``dto`` and end it, so that a further call sees none."""
    build = _plan_build.get()
    if build is None or build.dto is not dto:
        return None
    _plan_build.set(None)
    return build


def build_dto_plan(handler: BaseRouteHandler, app: Litestar) -> DTOPlan:
    """Resolve the DTOs of ``handler`` from its configuration and the serialization plugins of ``app``, and build
    their backends. It reads the handler and does not modify it; a second call returns an independent plan.

    Raises:
        DTOFactoryException: If a DTO cannot be applied, with the message prefixed by the handler's paths and name
        MissingDTOError: If the handler's data is annotated with ``DTOData`` and no DTO decodes it
    """
    with HandlerErrorPrefix.for_handler(handler).wrap_dto_exception():
        registry = app._transfer_model_registry
        data_field = handler.parsed_data_field
        data_dto, data_target = _resolve_data_dto(handler, app, data_field)
        data: DTODirectionPlan | None = None
        if data_field is not None and data_dto is not None and data_target is not None:
            data = _build_direction(
                data_dto, data_field, data_target, is_data_field=True, handler=handler, registry=registry
            )
        if data is None and data_field is not None and data_field.is_subclass_of(DTOData):
            raise MissingDTOError(handler_name=handler.handler_name, annotation=data_field.annotation)

        return_: DTODirectionPlan | None = None
        return_field = handler.parsed_return_field
        if resolved := _resolve_return_dto(handler, app, return_field, data_dto):
            return_dto, return_target = resolved
            return_ = _build_direction(
                return_dto, return_field, return_target, is_data_field=False, handler=handler, registry=registry
            )

        return DTOPlan(
            data=data,
            return_=return_,
            data_dto=data_dto,
            decode_bytes=(
                _create_decoder(data.dto, "decode_bytes", data.backend.populate_data_from_raw) if data else None
            ),
            decode_builtins=(
                _create_decoder(data.dto, "decode_builtins", data.backend.populate_data_from_builtins) if data else None
            ),
            encode=_create_encoder(return_.dto, return_.backend) if return_ else None,
        )


def _create_decoder(
    dto: type[AbstractDTO[Any]], name: Literal["decode_bytes", "decode_builtins"], backend_method: DecodeFn
) -> DecodeFn:
    if not dto._overrides(name):
        return dto._wrap_decoder(backend_method)
    if name == "decode_bytes":
        return lambda value, connection: dto(connection).decode_bytes(value)
    return lambda value, connection: dto(connection).decode_builtins(value)


def _create_encoder(dto: type[AbstractDTO[Any]], backend: DTOBackend) -> EncodeFn:
    if dto._overrides("data_to_encodable_type"):
        return lambda data, connection: dto(connection).data_to_encodable_type(data)

    encode_data = backend.encode_data

    def encode(data: Any, connection: ASGIConnection[Any, Any, Any, Any]) -> LitestarEncodableType:
        return encode_data(data)

    return encode


def _find_serialization_plugin(app: Litestar, field_definition: FieldDefinition) -> SerializationPlugin | None:
    return next(
        (
            plugin
            for plugin in app.plugins.serialization
            if field_definition.match_predicate_recursively(plugin.supports_type)
        ),
        None,
    )


def _resolve_data_dto(
    handler: BaseRouteHandler, app: Litestar, data_field: FieldDefinition | None
) -> tuple[type[AbstractDTO[Any]] | None, DTOTarget | None]:
    declaration = read_dto_declaration(handler, "dto")
    if declaration.value is None:
        return None, None
    if declaration.value is not Empty:
        dto = declaration.value
        if data_field is None:
            return dto, None
        if (target := resolve_dto_target(dto, data_field, "data")) is None and declaration.source == "handler":
            raise _not_applicable(declaration, dto, "data", data_field)
        return dto, target
    if data_field is not None and (plugin := _find_serialization_plugin(app, data_field)):
        plugin_dto = plugin.create_dto_for_type(data_field)
        if (target := resolve_dto_target(plugin_dto, data_field, "data")) is not None:
            return plugin_dto, target
    return None, None


def _resolve_return_dto(
    handler: BaseRouteHandler,
    app: Litestar,
    return_field: FieldDefinition,
    data_dto: type[AbstractDTO[Any]] | None,
) -> tuple[type[AbstractDTO[Any]], DTOTarget] | None:
    declaration = read_dto_declaration(handler, "return_dto")
    if declaration.value is None:
        return None
    if declaration.value is not Empty:
        dto = declaration.value
        if (target := resolve_dto_target(dto, return_field, "return")) is not None:
            return dto, target
        if declaration.source == "handler":
            raise _not_applicable(declaration, dto, "return", return_field)
        return None
    if data_dto is not None and (target := resolve_dto_target(data_dto, return_field, "return")) is not None:
        return data_dto, target
    if plugin := _find_serialization_plugin(app, return_field):
        plugin_dto = plugin.create_dto_for_type(return_field)
        if (target := resolve_dto_target(plugin_dto, return_field, "return")) is not None:
            return plugin_dto, target
    return None


def _format_annotation(annotation: Any) -> str:
    if annotation is NoneType:
        return "None"
    return _format_key(annotation) if isinstance(annotation, type) else repr(annotation)


def _not_applicable_reason(
    dto: type[AbstractDTO[Any]], direction: Literal["data", "return"], field_definition: FieldDefinition
) -> str | None:
    if (inner := _without_optional(field_definition)) is None:
        return None
    if direction == "data":
        if _is_form_collection(field_definition, inner):
            return "A form body is decoded into one model, not a collection."
        target = resolve_dto_target(dto, field_definition, "return")
        if target is not None and target.wrapper_attribute_name is not None:
            return "A generic wrapper is supported for return values only."
        return None
    if inner.origin in _STREAM_ORIGINS:
        return "Streamed items are not transferred by a DTO."
    return None


def _not_applicable(
    declaration: DTODeclaration,
    dto: type[AbstractDTO[Any]],
    direction: Literal["data", "return"],
    field_definition: FieldDefinition,
) -> DTONotApplicableError:
    name = dto_name(dto)
    annotation = _format_annotation(field_definition.annotation)
    declared = f"'{declaration.option}={name}' is declared on the handler"
    if direction == "return" and _resolve_target(dto, field_definition, direction, check_support=False) is not None:
        message = (
            f"{declared}, but {name}.is_supported_model_type_field() declines its return value annotated "
            f"'{annotation}'."
        )
    else:
        action = "decode its request body" if direction == "data" else "encode its return value"
        message = (
            f"{declared}, but cannot {action} annotated '{annotation}': the DTO handles "
            f"'{_format_key(dto.model_type)}'."  # pyright: ignore[reportGeneralTypeIssues]
        )
        if reason := _not_applicable_reason(dto, direction, field_definition):
            message = f"{message} {reason}"
    return DTONotApplicableError(
        message,
        dto=dto,
        option=declaration.option,
        direction=direction,
        annotation=field_definition.annotation,
    )


def _build_direction(
    dto: type[AbstractDTO[Any]],
    field_definition: FieldDefinition,
    target: DTOTarget,
    *,
    is_data_field: bool,
    handler: BaseRouteHandler,
    registry: TransferModelRegistry,
) -> DTODirectionPlan:
    name_scope = handler_name_scope(handler)
    if not dto._overrides("create_for_field_definition"):
        backend = create_backend(
            dto,
            field_definition,
            is_data_field=is_data_field,
            handler_id=str(handler.handler_id),
            registry=registry,
            name_scope=name_scope,
            target=target,
        )
    else:
        build = _PlanBuild(dto=dto, is_data_field=is_data_field, registry=registry, name_scope=name_scope)
        field = field_definition
        if is_data_field and not isinstance(field_definition.kwarg_definition, BodyKwarg):
            field = dataclasses.replace(field_definition, kwarg_definition=BodyKwarg())
        token = _plan_build.set(build)
        try:
            dto.create_for_field_definition(field_definition=field, handler_id=handler.handler_id)
        except AttributeError as exc:
            if exc.name != "_dto_backends":
                raise
            raise _no_backend_error(dto, handler) from exc
        finally:
            _plan_build.reset(token)
        if build.backend is None:
            raise _no_backend_error(dto, handler)
        backend = build.backend

    backend._bind_handler(type_decoders=handler.type_decoders, default_deserializer=handler.default_deserializer)
    return DTODirectionPlan(
        dto=dto, backend=backend, schema_annotation=build_schema_annotation(dto, backend, field_definition)
    )


def dto_name(dto: type[AbstractDTO[Any]]) -> str:
    """Name ``dto`` in an error message: its qualified name, or, for a class created by subscripting a DTO class,
    the name of that class subscripted with the name of the model, such as ``DataclassDTO[User]``.
    """
    name: str | None = getattr(dto, "__qualname__", None)
    if name is None:
        return repr(dto)
    model_type = getattr(dto, "model_type", None)
    if "[" in name and isinstance(model_type, type):
        return f"{name.split('[', 1)[0]}[{model_type.__qualname__}]"
    return name


def _no_backend_error(dto: type[AbstractDTO[Any]], handler: BaseRouteHandler) -> DTOFactoryException:
    return DTOFactoryException(
        f"{dto_name(dto)}.create_for_field_definition() created no backend for handler {handler}: an override must "
        "call the base method"
    )


def create_dto_openapi_schema(
    direction: DTODirectionPlan,
    field_definition: FieldDefinition,
    handler: BaseRouteHandler,
    schema_creator: SchemaCreator,
) -> Reference | Schema:
    """Return the OpenAPI schema of ``field_definition``, the handler's own field in ``direction``. A DTO class that
    overrides ``create_openapi_schema`` is called through it.
    """
    dto = direction.dto
    if dto._overrides("create_openapi_schema"):
        return dto.create_openapi_schema(
            field_definition=field_definition, handler_id=handler.handler_id, schema_creator=schema_creator
        )
    try:
        return schema_creator.for_field_definition(
            FieldDefinition.from_annotation(
                direction.schema_annotation, kwarg_definition=field_definition.kwarg_definition
            )
        )
    except TypeError as exc:
        with HandlerErrorPrefix.for_handler(handler).wrap_dto_exception():
            try:
                msgspec.json.Decoder(direction.backend.annotation, strict=False)
            except TypeError as decoder_exc:
                raise DTOTransferTypeError(
                    f"msgspec cannot describe the transfer model of {_qualified_name(direction.backend.model_type)!r}: "
                    f"{exc}"
                ) from decoder_exc
        raise
