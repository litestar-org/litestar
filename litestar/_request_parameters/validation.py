# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

import dataclasses
import re
from functools import partial
from pathlib import Path, PurePath
from typing import TYPE_CHECKING, Annotated, Any, Literal, Optional, TypedDict, Union
from uuid import UUID

from msgspec import NODEFAULT, UNSET, Meta, ValidationError, convert, defstruct

from litestar._request_parameters.extraction import RequestParameterExtractor
from litestar.datastructures.state import ImmutableState
from litestar.datastructures.url import URL
from litestar.dto import DTOData
from litestar.enums import ParamType, ScopeType
from litestar.exceptions import ClientException, SerializationException, ValidationException
from litestar.params import ParameterKwarg, SkipValidationMarker
from litestar.serialization import default_deserializer
from litestar.utils import get_origin_or_inner_type, is_class_and_subclass
from litestar.utils.dataclass import simple_asdict

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Coroutine, Iterable, Mapping
    from typing import NotRequired

    from litestar._request_parameters.declarations import RequestParameterDefinition
    from litestar.connection import ASGIConnection
    from litestar.dto._plan import DTOPlan
    from litestar.params import KwargDefinition
    from litestar.types import TypeDecodersSequence
    from litestar.typing import FieldDefinition

__all__ = ("RequestParameterValidationError", "RequestParameterValidator", "create_request_param_validaton_fn")


class ExtendedMsgSpecValidationError(ValidationError):
    def __init__(self, errors: list[dict[str, Any]]) -> None:
        self.errors = errors
        super().__init__(errors)


def _normalize_annotation(field_definition: FieldDefinition) -> Any:
    if field_definition.has_metadata(SkipValidationMarker):
        return Any

    return field_definition.annotation


def _get_decoder_for_type(target_type: Any, type_decoders: TypeDecodersSequence) -> Callable[[type, Any], Any] | None:
    return next(
        (decoder for predicate, decoder in type_decoders if predicate(target_type)),
        None,
    )


class ErrorMessage(TypedDict):
    # key may not be set in some cases, like when a query param is set but
    # doesn't match the required length during `attrs` validation
    # in this case, we don't show a key at all as it will be empty
    key: NotRequired[str]
    message: str
    source: NotRequired[Literal["body"] | ParamType]


ERR_RE = re.compile(r"`\$\.(.+)`$")

DEFAULT_TYPE_DECODERS = [
    (lambda x: is_class_and_subclass(x, (Path, PurePath, ImmutableState, UUID)), lambda t, v: t(v)),
]


def _deserializer(
    target_type: Any,
    value: Any,
    type_decoders: TypeDecodersSequence,
    default_deserializer: Callable[[Any, Any], Any],
) -> Any:
    if isinstance(value, DTOData):
        return value

    try:
        if isinstance(value, target_type):
            return value
    except TypeError as exc:
        if (origin := get_origin_or_inner_type(target_type)) is not None:
            if isinstance(value, origin):
                return value
        else:
            raise exc

    if decoder := _get_decoder_for_type(target_type, type_decoders):
        return decoder(target_type, value)

    return default_deserializer(target_type, value)


def _create_validation_exception(connection: ASGIConnection, messages: list[ErrorMessage]) -> ValidationException:
    """Create the ValidationException reporting ``messages`` for the request of ``connection``.

    Args:
        connection: An ASGI connection instance.
        messages: A list of error messages.

    Returns:
        A ValidationException
    """
    method = connection.method if hasattr(connection, "method") else ScopeType.WEBSOCKET  # pyright: ignore[reportAttributeAccessIssue]
    path = URL.from_components(
        path=connection.url.path,
        query=connection.url.query,
    )
    return ValidationException(detail=f"Validation failed for {method} {path}", extra=messages)


def _create_meta(kwarg_definition: KwargDefinition) -> Meta:
    """Create the msgspec ``Meta`` holding the constraints and documentation of ``kwarg_definition``."""
    meta_kwargs: dict[str, Any] = {"extra": {}}

    values = simple_asdict(kwarg_definition, exclude_empty=True)
    if min_items := values.pop("min_items", None):
        meta_kwargs["min_length"] = min_items
    if max_items := values.pop("max_items", None):
        meta_kwargs["max_length"] = max_items

    for k, v in values.items():
        if hasattr(Meta, k) and v is not None:
            meta_kwargs[k] = v
        else:
            meta_kwargs["extra"][k] = v

    return Meta(**meta_kwargs)


def _create_annotation(field_definition: FieldDefinition, meta_data: Meta | None = None) -> Any:
    annotation = _normalize_annotation(field_definition=field_definition)

    if annotation is Any:
        return annotation

    if field_definition.is_union:
        types = [
            _create_annotation(field_definition=inner_type, meta_data=meta_data)
            for inner_type in field_definition.inner_types
            if not inner_type.is_none_type
        ]
        return Optional[Union[tuple(types)]] if field_definition.is_optional else Union[tuple(types)]  # pyright: ignore # noqa: UP045

    if meta_data:
        annotation = Annotated[annotation, meta_data]
    return annotation


class RequestParameterValidationError(Exception):
    """Request parameters are missing or invalid"""

    def __init__(self, messages: list[ErrorMessage]) -> None:
        super().__init__(messages)
        self.messages = messages
        """One message per missing or invalid parameter"""


def _annotation_for(field_definition: FieldDefinition) -> Any:
    kwarg_definition = field_definition.kwarg_definition
    documentation_only = isinstance(kwarg_definition, ParameterKwarg) and kwarg_definition.documentation_only
    return _create_annotation(
        # the name of a declaring parameter must not decide how the value is validated
        field_definition=dataclasses.replace(field_definition, name=""),
        meta_data=_create_meta(kwarg_definition) if kwarg_definition and not documentation_only else None,
    )


def _struct_default(field_definition: FieldDefinition) -> Any:
    # a parameter can be required and have a default: 'QueryParameter(required=True)'
    if field_definition.is_required:
        return NODEFAULT
    # a layer parameter no parameter declares can be not required without a default
    return field_definition.default if field_definition.has_default else UNSET


class RequestParameterValidator:
    """Validate and convert raw values of request parameters, and the request body"""

    __slots__ = ("_attribute_keys", "_deserializer", "_fields", "_struct")

    def __init__(
        self,
        definitions: Iterable[RequestParameterDefinition],
        *,
        type_decoders: TypeDecodersSequence,
        skip_body_validation: bool = False,
    ) -> None:
        """Create a validator of the request parameters ``definitions`` define.

        Args:
            definitions: The request parameters to validate
            type_decoders: The type decoders applied to each parameter
            skip_body_validation: Pass the body on as it is given, because a DTO decodes it
        """
        fields: list[tuple[str, RequestParameterDefinition]] = []
        struct_fields: list[tuple[str, Any, Any]] = []
        for index, definition in enumerate(definitions):
            attribute = f"p{index}"
            annotation = (
                Any if definition.is_body and skip_body_validation else _annotation_for(definition.field_definition)
            )
            fields.append((attribute, definition))
            struct_fields.append((attribute, annotation, _struct_default(definition.field_definition)))
        self._fields = tuple(fields)
        """Each request parameter, with the name of its field on the Struct"""
        self._attribute_keys = tuple([(attribute, definition.key) for attribute, definition in fields])
        """The name of each field on the Struct, with the key of its request parameter"""
        # performance: each field is renamed to the key of its parameter, so that 'convert'
        # can read the raw values as they are. without it, a dict by attribute has to be
        # built for 'convert' on every request.
        self._struct = defstruct("RequestParameters", struct_fields, kw_only=True, rename=dict(self._attribute_keys))
        self._deserializer = partial(
            _deserializer,
            type_decoders=[*(type_decoders or []), *DEFAULT_TYPE_DECODERS],
            default_deserializer=partial(default_deserializer, type_decoders=type_decoders),
        )

    def validate(self, raw: Mapping[str, Any]) -> dict[str, Any]:
        """Return the value of each request parameter, by key, converted from ``raw``,
        the raw values present in a request by key. A parameter missing from ``raw`` that is
        neither required nor has a default has no value.

        Raises:
            RequestParameterValidationError: Listing each required parameter missing
                from ``raw`` and each invalid value.
        """
        try:
            # a required parameter is given no default on the Struct, so this raises for a missing one
            values = convert(raw, self._struct, strict=False, dec_hook=self._deserializer, str_keys=True)
        except ValidationError:
            pass
        else:
            return {
                key: value
                for attribute, key in self._attribute_keys
                if (value := getattr(values, attribute)) is not UNSET
            }

        messages: list[ErrorMessage] = []
        for attribute, definition in self._fields:
            if definition.key not in raw:
                if definition.field_definition.is_required:
                    messages.append(_missing_message(definition))
                continue
            try:
                convert(
                    raw[definition.key],
                    type=self._struct.__annotations__[attribute],
                    strict=False,
                    dec_hook=self._deserializer,
                    str_keys=True,
                )
            except ExtendedMsgSpecValidationError as exc:
                messages.extend(
                    _message(definition, [str(location) for location in error["loc"]], error["msg"])
                    for error in exc.errors
                )
            except ValidationError as exc:
                match = ERR_RE.search(str(exc))
                messages.append(_message(definition, [match.group(1)] if match else [], str(exc)))
        raise RequestParameterValidationError(messages)


def _missing_message(definition: RequestParameterDefinition) -> ErrorMessage:
    if definition.param_type is None:
        return {"message": "Missing required request body", "key": "data", "source": "body"}
    return {
        "message": f"Missing required {definition.param_type.value} parameter",
        "key": definition.name,
        "source": definition.param_type,
    }


def _message(definition: RequestParameterDefinition, path: list[str], message: str) -> ErrorMessage:
    text = message.split(" - ", maxsplit=1)[0]
    if definition.param_type is None:
        return {"message": text, "key": ".".join(path) if path else "data", "source": "body"}
    return {"message": text, "key": ".".join([definition.name, *path]), "source": definition.param_type}


def create_request_param_validaton_fn(
    definitions: Collection[RequestParameterDefinition],
    *,
    dto_plan: DTOPlan | None,
    type_decoders: TypeDecodersSequence,
) -> Callable[[ASGIConnection], Coroutine[Any, Any, dict[str, Any]]]:
    """Return the validation pass over the request parameters ``definitions`` define: a function
    that extracts them from a connection, validates them all and returns their values by key. It
    raises a :exc:`~litestar.exceptions.ClientException` if the body cannot be decoded, and a
    :exc:`~litestar.exceptions.ValidationException` listing each missing and each invalid parameter.

    Args:
        definitions: The request parameters of a handler
        dto_plan: The DTO plan decoding the body, if there is one
        type_decoders: The type decoders applied to each parameter
    """
    extractor = RequestParameterExtractor(definitions, dto_plan=dto_plan)
    validator = RequestParameterValidator(
        definitions,
        type_decoders=type_decoders,
        skip_body_validation=dto_plan is not None and dto_plan.data is not None,
    )

    async def validate_request_parameters(connection: ASGIConnection) -> dict[str, Any]:
        try:
            raw = await extractor.extract(connection)
        except SerializationException as exc:
            raise ClientException(str(exc)) from exc
        try:
            return validator.validate(raw)
        except RequestParameterValidationError as exc:
            raise _create_validation_exception(connection, exc.messages) from exc

    return validate_request_parameters
