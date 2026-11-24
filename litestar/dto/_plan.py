from __future__ import annotations

from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from dataclasses import dataclass
from types import NoneType
from typing import TYPE_CHECKING, Any, Literal, TypeAlias

import msgspec

from litestar._layers.errors import HandlerErrorPrefix
from litestar.di._helpers import _format_key
from litestar.dto._backend import DTOBackend
from litestar.dto._msgspec_rejection import qualified_name
from litestar.dto._registry import TransferModelNaming
from litestar.dto.data_structures import DTOData
from litestar.enums import RequestEncodingType
from litestar.exceptions.dto_exceptions import (
    DTONotApplicableError,
    DTOTransferTypeError,
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
    from litestar.types.empty import EmptyType
    from litestar.types.serialization import LitestarEncodableType

__all__ = (
    "DTOPlan",
    "DecodeFn",
    "EncodeFn",
    "build_dto_plan",
    "build_schema_annotation",
    "create_backend",
    "create_dto_openapi_schema",
    "dto_name",
    "read_dto_declaration",
    "resolve_dto_target",
)

DecodeFn: TypeAlias = "Callable[[Any, ASGIConnection[Any, Any, Any, Any]], Any]"
EncodeFn: TypeAlias = "Callable[[Any], LitestarEncodableType]"


@dataclass(frozen=True, slots=True)
class DTODirectionPlan:
    """How a route handler applies a DTO in one direction, to the data it receives or to the data it returns."""

    dto: type[AbstractDTO[Any]]
    """The DTO class applied in this direction"""
    backend: DTOBackend
    """The backend built for the handler's own field in this direction, bound to the handler's type decoders"""
    schema_annotation: Any
    """The annotation the field is documented with in the OpenAPI schema"""

    @property
    def passes_none(self) -> bool:
        """Whether the annotation is optional, so that ``None`` passes through without the DTO"""
        return self.backend._passes_none


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


def read_dto_declaration(
    handler: BaseRouteHandler, *, is_data_field: bool
) -> tuple[type[AbstractDTO[Any]] | None | EmptyType, bool]:
    """Return the declared ``dto`` if ``is_data_field``, otherwise the declared ``return_dto``, of ``handler``, and
    whether the handler declares it itself: its own value if it declares one, otherwise the value of the closest
    layer above it that declares one, ``Empty`` if none does.
    """
    own, inherited = (
        (handler._dto, handler._inherited_dto)
        if is_data_field
        else (handler._return_dto, handler._inherited_return_dto)
    )
    return (own, True) if own is not Empty else (inherited, False)


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


def _model_type(dto: type[AbstractDTO[Any]]) -> Any:
    return dto.model_type  # pyright: ignore[reportGeneralTypeIssues]


def _is_form_body(field_definition: FieldDefinition) -> bool:
    kwarg_definition = field_definition.kwarg_definition
    return isinstance(kwarg_definition, BodyKwarg) and kwarg_definition.media_type in _FORM_MEDIA_TYPES


def _is_form_collection(field_definition: FieldDefinition, inner: FieldDefinition) -> bool:
    data = inner.inner_types[0] if inner.is_subclass_of(DTOData) and inner.inner_types else inner
    return _is_form_body(field_definition) and data.is_collection


def resolve_dto_target(
    dto: type[AbstractDTO[Any]], field_definition: FieldDefinition | None, *, is_data_field: bool
) -> DTOTarget | None:
    """Return what ``dto`` applies to in ``field_definition``, the data a handler receives if ``is_data_field``,
    otherwise the data it returns, or ``None`` if it cannot be applied to it.

    The DTO applies to an annotation without ``None``, or to the first member of an optional annotation that is not
    ``None``, whose model type, unwrapped from ``DTOData``, a collection, a mapping value or a variadic tuple, is a
    subclass of the DTO's model type, except for a collection or mapping on a form body. In the return direction
    the DTO must also support that annotation, and it applies to a model wrapped in a generic type.
    """
    if (
        not is_data_field
        and (inner := _without_optional(field_definition)) is not None
        and not dto.is_supported_model_type_field(inner)
    ):
        return None
    return _match_target(dto, field_definition, is_data_field=is_data_field)


def _match_target(
    dto: type[AbstractDTO[Any]], field_definition: FieldDefinition | None, *, is_data_field: bool
) -> DTOTarget | None:
    if (inner := _without_optional(field_definition)) is None or field_definition is None:
        return None
    if not inner.inner_types and inner.is_subclass_of(_model_type(dto)):
        model_field = inner
    elif not inner.inner_types and (inner.is_collection or inner.is_subclass_of(DTOData)):
        return None
    else:
        model_field = dto.resolve_model_type(inner)

    passes_none = field_definition.is_optional
    if model_field.is_subclass_of(_model_type(dto)):
        if is_data_field and model_field is not inner and _is_form_collection(field_definition, inner):
            return None
        return DTOTarget(
            model_field=model_field,
            transfer_field=field_definition,
            wrapper_attribute_name=None,
            passes_none=passes_none,
        )

    if (
        not is_data_field
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
        )
    return None


def create_backend(
    dto: type[AbstractDTO[Any]],
    target: DTOTarget,
    *,
    is_data_field: bool,
    handler_id: str,
    naming: TransferModelNaming | None = None,
    backend_cls: type[DTOBackend] = DTOBackend,
) -> DTOBackend:
    """Create the backend of ``dto`` for ``target``, in the data a handler receives if ``is_data_field``, otherwise
    in the data it returns. Every backend is created here.

    The backend names its transfer models through ``naming``, or, without it, in a registry of its own.
    """
    keywords: dict[str, Any] = {"naming": naming} if naming is not None else {}
    backend = backend_cls(
        dto_factory=dto,
        field_definition=target.transfer_field,
        model_type=target.model_field.annotation,
        wrapper_attribute_name=target.wrapper_attribute_name,
        is_data_field=is_data_field,
        handler_id=handler_id,
        **keywords,
    )
    backend._passes_none = target.passes_none
    return backend


def build_schema_annotation(dto: type[AbstractDTO[Any]], backend: DTOBackend, field_definition: FieldDefinition) -> Any:
    """Return the annotation to document ``field_definition`` with: the backend's annotation, or, for a model
    wrapped in a generic type other than a ``Response``, the outer generic type with the model replaced by the
    transfer model.
    """
    if backend.wrapper_attribute_name and not field_definition.is_subclass_of(Response):
        model_type = _model_type(dto)
        generic_args = tuple(backend.transfer_model_type if arg is model_type else arg for arg in field_definition.args)
        return field_definition.safe_generic_origin[generic_args]
    return backend.annotation


def handler_name_scope(handler: BaseRouteHandler) -> Hashable:
    """Return the value that identifies ``handler`` for naming, equal for every merge of the same registration."""
    return (
        str(handler),
        type(handler).__qualname__,
        tuple(sorted(handler.paths)),
        tuple(sorted(getattr(handler, "http_methods", ()))),
    )


def build_dto_plan(handler: BaseRouteHandler, app: Litestar) -> DTOPlan:
    """Resolve the DTOs of ``handler`` from its configuration and the serialization plugins of ``app``, and build
    their backends. It reads the handler and does not modify it; a second call returns an independent plan.

    Raises:
        DTOFactoryException: If a DTO cannot be applied, with the message prefixed by the handler's paths and name
        MissingDTOError: If the handler's data is annotated with ``DTOData`` and no DTO decodes it
    """
    with HandlerErrorPrefix.for_handler(handler).wrap_dto_exception():
        registry = app._transfer_model_registry
        name_scope = handler_name_scope(handler)
        data_field = handler.parsed_data_field
        data_dto, data_target = _resolve_data_dto(handler, app, data_field)
        data: DTODirectionPlan | None = None
        if data_field is not None and data_dto is not None and data_target is not None:
            data = _build_direction(
                data_dto,
                data_field,
                data_target,
                is_data_field=True,
                handler=handler,
                naming=TransferModelNaming(registry, name_scope),
            )
        if data is None and data_field is not None and data_field.is_subclass_of(DTOData):
            raise MissingDTOError(
                f"The data it receives is annotated '{_format_annotation(data_field.annotation)}', but no DTO "
                "decodes it. Declare 'dto=' on the handler with a DTO that handles the model.",
                annotation=data_field.annotation,
            )

        return_: DTODirectionPlan | None = None
        return_field = handler.parsed_return_field
        if resolved := _resolve_return_dto(handler, app, return_field, data_dto):
            return_dto, return_target = resolved
            return_ = _build_direction(
                return_dto,
                return_field,
                return_target,
                is_data_field=False,
                handler=handler,
                naming=TransferModelNaming(registry, name_scope),
            )

        return DTOPlan(
            data=data,
            return_=return_,
            data_dto=data_dto,
            decode_bytes=data.dto._wrap_decoder(data.backend.populate_data_from_raw) if data else None,
            decode_builtins=data.dto._wrap_decoder(data.backend.populate_data_from_builtins) if data else None,
            encode=return_.backend.encode_data if return_ else None,
        )


def _plugin_dto(
    app: Litestar, field_definition: FieldDefinition, *, is_data_field: bool
) -> tuple[type[AbstractDTO[Any]], DTOTarget] | None:
    plugin = next(
        (
            plugin
            for plugin in app.plugins.serialization
            if field_definition.match_predicate_recursively(plugin.supports_type)
        ),
        None,
    )
    if plugin is not None:
        plugin_dto = plugin.create_dto_for_type(field_definition)
        if (target := resolve_dto_target(plugin_dto, field_definition, is_data_field=is_data_field)) is not None:
            return plugin_dto, target
    return None


def _resolve_data_dto(
    handler: BaseRouteHandler, app: Litestar, data_field: FieldDefinition | None
) -> tuple[type[AbstractDTO[Any]] | None, DTOTarget | None]:
    dto, declared_on_handler = read_dto_declaration(handler, is_data_field=True)
    if dto is None:
        return None, None
    if dto is not Empty:
        if data_field is None:
            return dto, None
        if (target := resolve_dto_target(dto, data_field, is_data_field=True)) is None and (
            declared_on_handler or _mentions_model(data_field, dto)
        ):
            raise _not_applicable(dto, data_field, is_data_field=True, declared_on_handler=declared_on_handler)
        return dto, target
    if data_field is not None and (plugin_dto := _plugin_dto(app, data_field, is_data_field=True)):
        return plugin_dto
    return None, None


def _resolve_return_dto(
    handler: BaseRouteHandler,
    app: Litestar,
    return_field: FieldDefinition,
    data_dto: type[AbstractDTO[Any]] | None,
) -> tuple[type[AbstractDTO[Any]], DTOTarget] | None:
    dto, declared_on_handler = read_dto_declaration(handler, is_data_field=False)
    if dto is None:
        return None
    if dto is not Empty:
        if (target := resolve_dto_target(dto, return_field, is_data_field=False)) is not None:
            return dto, target
        if declared_on_handler or _mentions_model(return_field, dto):
            raise _not_applicable(dto, return_field, is_data_field=False, declared_on_handler=declared_on_handler)
        return None
    if data_dto is not None and (target := resolve_dto_target(data_dto, return_field, is_data_field=False)) is not None:
        return data_dto, target
    return _plugin_dto(app, return_field, is_data_field=False)


def _format_annotation(annotation: Any) -> str:
    if annotation is NoneType:
        return "None"
    return _format_key(annotation) if isinstance(annotation, type) else repr(annotation)


def _not_applicable_reason(
    dto: type[AbstractDTO[Any]], field_definition: FieldDefinition, *, is_data_field: bool
) -> str | None:
    if (inner := _without_optional(field_definition)) is None:
        return None
    if is_data_field:
        if _is_form_collection(field_definition, inner):
            return "A form body is decoded into one model, not a collection."
        target = resolve_dto_target(dto, field_definition, is_data_field=False)
        if target is not None and target.wrapper_attribute_name is not None:
            return "A generic wrapper is supported for return values only."
        return None
    if inner.origin in _STREAM_ORIGINS:
        return "Streamed items are not transferred by a DTO."
    return None


def _mentions_model(field_definition: FieldDefinition, dto: type[AbstractDTO[Any]]) -> bool:
    model_type = _model_type(dto)
    return any(
        inner.match_predicate_recursively(lambda field: field.is_subclass_of(model_type))
        for inner in field_definition.inner_types
    )


def _not_applicable(
    dto: type[AbstractDTO[Any]], field_definition: FieldDefinition, *, is_data_field: bool, declared_on_handler: bool
) -> DTONotApplicableError:
    option: Literal["dto", "return_dto"] = "dto" if is_data_field else "return_dto"
    name = dto_name(dto)
    annotation = _format_annotation(field_definition.annotation)
    declared = f"'{option}={name}' is declared on {'the handler' if declared_on_handler else 'a layer'}"
    if not is_data_field and _match_target(dto, field_definition, is_data_field=False) is not None:
        message = (
            f"{declared}, but {name}.is_supported_model_type_field() declines its return value annotated "
            f"'{annotation}'."
        )
    else:
        action = "decode its request body" if is_data_field else "encode its return value"
        message = (
            f"{declared}, but cannot {action} annotated '{annotation}': the DTO handles "
            f"'{_format_key(_model_type(dto))}'."
        )
        if reason := _not_applicable_reason(dto, field_definition, is_data_field=is_data_field):
            message = f"{message} {reason}"
    if not declared_on_handler:
        message = f"{message} Declare '{option}=None' on the handler to opt out."
    return DTONotApplicableError(
        message,
        dto=dto,
        option=option,
        annotation=field_definition.annotation,
    )


def _build_direction(
    dto: type[AbstractDTO[Any]],
    field_definition: FieldDefinition,
    target: DTOTarget,
    *,
    is_data_field: bool,
    handler: BaseRouteHandler,
    naming: TransferModelNaming,
) -> DTODirectionPlan:
    backend = create_backend(dto, target, is_data_field=is_data_field, handler_id=handler.handler_id, naming=naming)
    backend._bind_handler(type_decoders=handler.type_decoders, default_deserializer=handler.default_deserializer)
    return DTODirectionPlan(
        dto=dto,
        backend=backend,
        schema_annotation=build_schema_annotation(dto, backend, field_definition),
    )


def dto_name(dto: type[AbstractDTO[Any]]) -> str:
    """Name ``dto`` in an error message: its qualified name, or, for a class created by subscripting a DTO class,
    the name of that class subscripted with the name of the model, such as ``DataclassDTO[User]``.
    """
    name = dto.__qualname__
    model_type = getattr(dto, "model_type", None)
    if "[" in name and isinstance(model_type, type):
        return f"{name.split('[', 1)[0]}[{model_type.__qualname__}]"
    return name


def create_dto_openapi_schema(
    direction_plan: DTODirectionPlan,
    field_definition: FieldDefinition,
    handler: BaseRouteHandler,
    schema_creator: SchemaCreator,
) -> Reference | Schema:
    """Return the OpenAPI schema of ``field_definition``, the handler's own field in ``direction_plan``."""
    try:
        return schema_creator.for_field_definition(
            FieldDefinition.from_annotation(
                direction_plan.schema_annotation, kwarg_definition=field_definition.kwarg_definition
            )
        )
    except TypeError as exc:
        with HandlerErrorPrefix.for_handler(handler).wrap_dto_exception():
            try:
                msgspec.json.Decoder(direction_plan.backend.annotation, strict=False)
            except TypeError as decoder_exc:
                raise DTOTransferTypeError(
                    f"msgspec cannot describe the transfer model of {qualified_name(direction_plan.backend.model_type)!r}: "
                    f"{exc}"
                ) from decoder_exc
        raise
