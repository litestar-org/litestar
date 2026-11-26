from collections.abc import AsyncGenerator, AsyncIterator, Generator, Iterator
from dataclasses import dataclass
from types import NoneType
from typing import TYPE_CHECKING, Any, Literal, Union

from litestar.di._helpers import _format_key
from litestar.dto._backend import build_annotation_for_backend
from litestar.dto.data_structures import DTOData
from litestar.enums import RequestEncodingType
from litestar.exceptions.dto_exceptions import DTONotApplicableError, MissingDTOError
from litestar.params import BodyKwarg
from litestar.response.base import Response
from litestar.types import Empty
from litestar.typing import FieldDefinition

if TYPE_CHECKING:
    from litestar.app import Litestar
    from litestar.dto._backend import DTOBackend
    from litestar.dto.base_dto import AbstractDTO
    from litestar.handlers.base import BaseRouteHandler
    from litestar.plugins import SerializationPlugin
    from litestar.types.empty import EmptyType

__all__ = (
    "DTOTarget",
    "build_schema_annotation",
    "read_dto_declaration",
    "resolve_data_backend",
    "resolve_dto_target",
    "resolve_return_backend",
)


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


def read_dto_declaration(
    handler: "BaseRouteHandler", *, is_data_field: bool
) -> "tuple[type[AbstractDTO[Any]] | None | EmptyType, bool]":
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


def resolve_data_backend(
    handler: "BaseRouteHandler", app: "Litestar"
) -> "tuple[type[AbstractDTO[Any]] | None, DTOBackend | None]":
    """Return the data DTO of ``handler`` and the backend it decodes the handler's data with, ``None`` if it does not
    apply to the data or the handler receives none. A DTO declared on the handler must apply; one declared on a layer
    or created by a serialization plugin is skipped if the annotation does not mention its model.

    Raises:
        DTONotApplicableError: If the DTO cannot be applied
        MissingDTOError: If the data is annotated with ``DTOData`` and no DTO decodes it
    """
    data_field = handler.parsed_data_field
    dto, target = _resolve_data_dto(handler, app, data_field)
    backend = None
    if data_field is not None and dto is not None and target is not None:
        backend = _create_backend(dto, data_field, handler, app)
    if (
        backend is None
        and data_field is not None
        and (inner := _without_optional(data_field)) is not None
        and inner.is_subclass_of(DTOData)
    ):
        raise MissingDTOError(
            f"The data it receives is annotated '{_format_annotation(data_field.annotation)}', but no DTO "
            "decodes it. Declare 'dto=' on the handler with a DTO that handles the model.",
            annotation=data_field.annotation,
        )
    return dto, backend


def resolve_return_backend(
    handler: "BaseRouteHandler", app: "Litestar", data_dto: "type[AbstractDTO[Any]] | None"
) -> "tuple[type[AbstractDTO[Any]], DTOBackend] | tuple[None, None]":
    """Return the DTO ``handler`` encodes its return value with and its backend, ``None`` if no DTO applies to it.
    Without a declared ``return_dto``, the data DTO ``data_dto`` is used if it handles the return annotation.

    Raises:
        DTONotApplicableError: If the DTO cannot be applied
    """
    return_field = handler.parsed_return_field
    if resolved := _resolve_return_dto(handler, app, return_field, data_dto):
        return resolved[0], _create_backend(resolved[0], return_field, handler, app)
    return None, None


def _create_backend(
    dto: "type[AbstractDTO[Any]]", field_definition: FieldDefinition, handler: "BaseRouteHandler", app: "Litestar"
) -> "DTOBackend":
    return dto.create_for_field_definition(
        field_definition=field_definition, handler_id=handler.handler_id, transfer_models=app._dto_transfer_models
    )


def _without_optional(field_definition: FieldDefinition | None) -> FieldDefinition | None:
    if field_definition is None:
        return None
    annotation = field_definition.annotation
    if annotation is Empty or annotation is None or annotation is NoneType:
        return None
    if field_definition.is_optional:
        non_none = [inner for inner in field_definition.inner_types if not inner.is_subclass_of(NoneType)]
        return non_none[0] if len(non_none) == 1 else field_definition
    return field_definition


def _model_type(dto: "type[AbstractDTO[Any]]") -> Any:
    return dto.model_type  # pyright: ignore[reportGeneralTypeIssues]


def _is_form_body(field_definition: FieldDefinition) -> bool:
    kwarg_definition = field_definition.kwarg_definition
    return isinstance(kwarg_definition, BodyKwarg) and kwarg_definition.media_type in _FORM_MEDIA_TYPES


def _is_form_collection(field_definition: FieldDefinition, inner: FieldDefinition) -> bool:
    data = inner.inner_types[0] if inner.is_subclass_of(DTOData) and inner.inner_types else inner
    return _is_form_body(field_definition) and data.is_collection


def resolve_dto_target(
    dto: "type[AbstractDTO[Any]]", field_definition: FieldDefinition | None, *, is_data_field: bool
) -> DTOTarget | None:
    """Return what ``dto`` applies to in ``field_definition``, the data a handler receives if ``is_data_field``,
    otherwise the data it returns, or ``None`` if it cannot be applied to it.

    The DTO applies to an annotation without ``None``, or to the only member of an optional annotation that is not
    ``None``, whose model type, unwrapped from ``DTOData``, a collection, a mapping value or a variadic tuple, is a
    subclass of the DTO's model type, except for a collection or mapping on a form body. In the return direction
    the DTO must also support that annotation, and it applies to a model wrapped in a generic type, or in a union of
    generic types that hold it in the same attribute.
    """
    if (
        not is_data_field
        and (inner := _without_optional(field_definition)) is not None
        and not all(dto.is_supported_model_type_field(member) for member in _union_members(inner))
    ):
        return None
    return _match_target(dto, field_definition, is_data_field=is_data_field)


def _match_target(
    dto: "type[AbstractDTO[Any]]", field_definition: FieldDefinition | None, *, is_data_field: bool
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

    if is_data_field or model_field is not inner:
        return None
    if any(_wrapper_rejection(dto, member) for member in _union_members(inner)):
        return None
    first, *others = [_match_wrapper(dto, member) for member in _union_members(inner)]
    if first is None or any(other is None or _wrapper_key(other) != _wrapper_key(first) for other in others):
        return None
    model_field, transfer_field, wrapper_attribute_name = first
    return DTOTarget(
        model_field=model_field,
        transfer_field=transfer_field,
        wrapper_attribute_name=wrapper_attribute_name,
        passes_none=passes_none,
    )


def _union_members(field_definition: FieldDefinition) -> tuple[FieldDefinition, ...]:
    if not field_definition.is_union:
        return (field_definition,)
    return tuple(inner for inner in field_definition.inner_types if not inner.is_subclass_of(NoneType))


def _match_wrapper(
    dto: "type[AbstractDTO[Any]]", field_definition: FieldDefinition
) -> tuple[FieldDefinition, FieldDefinition, str] | None:
    if field_definition.is_union:
        return None
    return dto.resolve_generic_wrapper_type(field_definition)


def _wrapper_rejection(dto: "type[AbstractDTO[Any]]", field_definition: FieldDefinition) -> str | None:
    if field_definition.is_union or not (wrapped := dto.resolve_generic_wrapper_type(field_definition)):
        return None
    if len(names := _model_attributes(dto, field_definition)) > 1:
        return f"More than one attribute of the generic wrapper holds the model: {', '.join(map(repr, names))}."
    if wrapped[1].match_predicate_recursively(
        lambda inner: (
            bool(inner.inner_types) and not inner.is_collection and not inner.is_union and _mentions_model(inner, dto)
        )
    ):
        return f"The attribute {wrapped[2]!r} holds the model inside another generic type."
    return None


def _model_attributes(dto: "type[AbstractDTO[Any]]", field_definition: FieldDefinition) -> list[str]:
    model_type = _model_type(dto)

    def holds_model(field: FieldDefinition) -> bool:
        return field.is_subclass_of(model_type) or _mentions_model(field, dto)

    parameters = getattr(field_definition.origin, "__parameters__", ())
    bound = tuple(
        parameter
        for parameter, inner in zip(parameters, field_definition.inner_types, strict=True)
        if inner.match_predicate_recursively(holds_model)
    )
    return [
        name
        for name, attribute in dto.get_model_type_hints(field_definition.origin).items()
        if attribute.match_predicate_recursively(lambda field: field.annotation in bound or holds_model(field))
    ]


def _wrapper_key(wrapped: tuple[FieldDefinition, FieldDefinition, str]) -> tuple[Any, Any, str]:
    model_field, transfer_field, wrapper_attribute_name = wrapped
    return model_field.annotation, transfer_field.annotation, wrapper_attribute_name


def build_schema_annotation(
    dto: "type[AbstractDTO[Any]]", backend: "DTOBackend", field_definition: FieldDefinition
) -> Any:
    """Return the annotation to document ``field_definition`` with: the backend's annotation, or, for a model
    wrapped in a generic type other than a ``Response``, the outer generic type with the model replaced by the
    transfer model in each of its arguments. An optional annotation stays optional.
    """
    inner = _without_optional(field_definition)
    if not backend.wrapper_attribute_name or inner is None:
        return backend.annotation
    model_type = _model_type(dto)
    annotation: Any = Union[
        tuple(
            backend.annotation
            if member.is_subclass_of(Response)
            else member.safe_generic_origin[
                tuple(
                    build_annotation_for_backend(model_type, inner_type, backend.transfer_model_type)
                    if dto.resolve_model_type(inner_type).is_subclass_of(model_type)
                    else arg
                    for arg, inner_type in zip(member.args, member.inner_types, strict=True)
                )
            ]
            for member in _union_members(inner)
        )
    ]
    return Union[annotation, None] if field_definition.is_optional else annotation


def _plugin_dto(
    app: "Litestar", field_definition: FieldDefinition, *, is_data_field: bool
) -> "tuple[type[AbstractDTO[Any]], DTOTarget] | None":

    def supported_by(plugin: "SerializationPlugin") -> bool:
        def supports(field: FieldDefinition) -> bool:
            supertype = getattr(field.annotation, "__supertype__", None)
            return plugin.supports_type(field) or (
                supertype is not None
                and FieldDefinition.from_annotation(supertype).match_predicate_recursively(supports)
            )

        return field_definition.match_predicate_recursively(supports)

    plugin = next((plugin for plugin in app.plugins.serialization if supported_by(plugin)), None)
    if plugin is not None:
        plugin_dto = plugin.create_dto_for_type(field_definition)
        if (target := resolve_dto_target(plugin_dto, field_definition, is_data_field=is_data_field)) is not None:
            return plugin_dto, target
        if _mentions_model(field_definition, plugin_dto) or not field_definition.match_predicate_recursively(
            plugin.supports_type
        ):
            raise _not_applicable(
                plugin_dto, field_definition, is_data_field=is_data_field, declared_on_handler=False, from_plugin=True
            )
    return None


def _resolve_data_dto(
    handler: "BaseRouteHandler", app: "Litestar", data_field: FieldDefinition | None
) -> "tuple[type[AbstractDTO[Any]] | None, DTOTarget | None]":
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
    handler: "BaseRouteHandler",
    app: "Litestar",
    return_field: FieldDefinition,
    data_dto: "type[AbstractDTO[Any]] | None",
) -> "tuple[type[AbstractDTO[Any]], DTOTarget] | None":
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
    declared_dto, dto_on_handler = read_dto_declaration(handler, is_data_field=True)
    if data_dto is not None and declared_dto is data_dto and _mentions_model(return_field, data_dto):
        raise _not_applicable(
            data_dto, return_field, is_data_field=False, declared_on_handler=dto_on_handler, reused=True
        )
    return _plugin_dto(app, return_field, is_data_field=False)


def _format_annotation(annotation: Any) -> str:
    if annotation is NoneType:
        return "None"
    return _format_key(annotation) if isinstance(annotation, type) else repr(annotation)


def _not_applicable_reason(
    dto: "type[AbstractDTO[Any]]", field_definition: FieldDefinition, *, is_data_field: bool
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
    return next(filter(None, (_wrapper_rejection(dto, member) for member in _union_members(inner))), None)


def _mentions_model(field_definition: FieldDefinition, dto: "type[AbstractDTO[Any]]") -> bool:
    model_type = _model_type(dto)

    def mentions(field: FieldDefinition) -> bool:
        if (supertype := getattr(field.annotation, "__supertype__", None)) is not None:
            return FieldDefinition.from_annotation(supertype).match_predicate_recursively(mentions)
        return field.is_subclass_of(model_type)

    fields = (
        (field_definition,) if hasattr(field_definition.annotation, "__supertype__") else field_definition.inner_types
    )
    return any(field.match_predicate_recursively(mentions) for field in fields)


def _not_applicable(
    dto: "type[AbstractDTO[Any]]",
    field_definition: FieldDefinition,
    *,
    is_data_field: bool,
    declared_on_handler: bool,
    reused: bool = False,
    from_plugin: bool = False,
) -> DTONotApplicableError:
    option: Literal["dto", "return_dto"] = "dto" if is_data_field or reused else "return_dto"
    name = _dto_name(dto)
    annotation = _format_annotation(field_definition.annotation)
    declared = (
        f"{name} is created by a serialization plugin"
        if from_plugin
        else f"'{option}={name}' is declared on {'the handler' if declared_on_handler else 'a layer'}"
    )
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
    if not declared_on_handler or reused:
        message = f"{message} Declare '{'dto' if is_data_field else 'return_dto'}=None' on the handler to opt out."
    return DTONotApplicableError(
        message,
        dto=dto,
        option=option,
        annotation=field_definition.annotation,
    )


def _dto_name(dto: "type[AbstractDTO[Any]]") -> str:
    name = dto.__qualname__
    model_type = getattr(dto, "model_type", None)
    if "[" in name and isinstance(model_type, type):
        return f"{name.split('[', 1)[0]}[{model_type.__qualname__}]"
    return name
