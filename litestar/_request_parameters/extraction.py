# pyright: reportUnnecessaryTypeIgnoreComment=false

from __future__ import annotations

from collections import defaultdict
from functools import lru_cache, partial
from typing import TYPE_CHECKING, Any, cast

from litestar._multipart import get_charset_table, parse_multipart_form
from litestar._parsers import (
    parse_query_string,
    parse_url_encoded_form_data,
)
from litestar.datastructures import Headers
from litestar.datastructures.upload_file import UploadFile
from litestar.enums import ParamType, RequestEncodingType
from litestar.params import BodyKwarg
from litestar.types import Empty
from litestar.utils import make_non_optional_union
from litestar.utils.predicates import is_non_string_sequence, is_optional_union
from litestar.utils.scope.state import ScopeState

if TYPE_CHECKING:
    from collections.abc import Callable, Coroutine, Iterable

    from litestar._request_parameters.declarations import RequestParameterDefinition
    from litestar.connection import ASGIConnection, Request
    from litestar.dto._plan import DecodeFn, DTOPlan
    from litestar.typing import FieldDefinition

__all__ = ("RequestParameterExtractor",)


@lru_cache(1024)
def create_query_default_dict(
    parsed_query: tuple[tuple[str, str], ...], sequence_query_parameter_names: frozenset[str]
) -> defaultdict[str, list[str] | str]:
    """Transform a list of tuples into a default dict. Ensures non-list values are not wrapped in a list.

    Args:
        parsed_query: The parsed query list of tuples.
        sequence_query_parameter_names: A set of query parameters that should be wrapped in list.

    Returns:
        A default dict
    """
    output: defaultdict[str, list[str] | str] = defaultdict(list)

    for k, v in parsed_query:
        if k in sequence_query_parameter_names:
            output[k].append(v)  # type: ignore[union-attr]
        else:
            output[k] = v

    return output


def parse_query_params(connection: ASGIConnection, sequence_query_parameter_names: frozenset[str]) -> dict[str, Any]:
    """Parse query params and cache the result in scope.

    Args:
        connection: The ASGI connection instance.
        sequence_query_parameter_names: The query parameters whose values are collected in a list.

    Returns:
        A dictionary of parsed values.
    """
    parsed_query = (
        connection._parsed_query
        if connection._parsed_query is not Empty
        else parse_query_string(connection.scope.get("query_string", b""))
    )
    ScopeState.from_scope(connection.scope).parsed_query = parsed_query
    return create_query_default_dict(
        parsed_query=parsed_query,
        sequence_query_parameter_names=sequence_query_parameter_names,
    )


def parse_headers(connection: ASGIConnection) -> Headers:
    """Parse header parameters and cache the result in scope.

    Args:
        connection: The ASGI connection instance.

    Returns:
        A Headers instance
    """
    return Headers.from_scope(connection.scope)


async def json_extractor(connection: Request[Any, Any, Any]) -> Any:
    """Decode the request's body as JSON.

    Args:
        connection: The ASGI connection instance.

    Returns:
        The JSON value, or ``Empty`` if the body is empty.
    """
    if not await connection.body():
        return Empty
    return await connection.json()


async def msgpack_extractor(connection: Request[Any, Any, Any]) -> Any:
    """Decode the request's body as MessagePack.

    Args:
        connection: The ASGI connection instance.

    Returns:
        The MessagePack value, or ``Empty`` if the body is empty.
    """
    if not await connection.body():
        return Empty
    return await connection.msgpack()


async def _extract_multipart(
    connection: Request[Any, Any, Any],
    body_kwarg_multipart_form_part_limit: int | None,
    field_definition: FieldDefinition,
    is_data_optional: bool,
    decode_builtins: DecodeFn | None,
) -> Any:
    multipart_form_part_limit = (
        body_kwarg_multipart_form_part_limit
        if body_kwarg_multipart_form_part_limit is not None
        else connection.app.multipart_form_part_limit
    )
    scope_state = ScopeState.from_scope(connection.scope)
    if scope_state.form is Empty:
        scope_state.form = form_values = await parse_multipart_form(
            stream=connection.stream(),
            boundary=connection.content_type[-1].get("boundary", "").encode(),
            multipart_form_part_limit=multipart_form_part_limit,
            type_decoders=connection.route_handler.type_decoders,
            charsets=get_charset_table(connection.app.multipart_form_allowed_charsets),
        )
    else:
        form_values = scope_state.form

    if field_definition.is_non_string_sequence:
        values = list(form_values.values())
        if isinstance(values[0], list) and (
            field_definition.has_inner_subclass_of(UploadFile)
            or (field_definition.is_optional and field_definition.inner_types[0].is_non_string_sequence)
        ):
            return values[0]

        return values

    if field_definition.is_simple_type and field_definition.annotation is UploadFile and form_values:
        return next(v for v in form_values.values() if isinstance(v, UploadFile))

    if not form_values and is_data_optional:
        return None

    if decode_builtins:
        return decode_builtins(form_values, connection)

    for name, tp in field_definition.get_type_hints().items():
        value = form_values.get(name)
        if value == "" and is_optional_union(tp):
            inner: Any = make_non_optional_union(tp)
            if isinstance(inner, type) and issubclass(inner, UploadFile):
                form_values[name] = None  # pyright: ignore[reportArgumentType]
                continue
        if (
            value is not None
            and not isinstance(value, list)
            and (
                is_non_string_sequence(tp)
                or (is_optional_union(tp) and is_non_string_sequence(make_non_optional_union(tp)))
            )
        ):
            form_values[name] = [value]  # pyright: ignore[reportArgumentType]
    return form_values


def create_multipart_extractor(
    field_definition: FieldDefinition, body_kwarg: BodyKwarg, is_data_optional: bool, decode_builtins: DecodeFn | None
) -> Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]:
    """Create a multipart form-data extractor.

    Args:
        field_definition: A FieldDefinition instance.
        body_kwarg: The body marker.
        is_data_optional: Boolean dictating whether the field is optional.
        decode_builtins: The data DTO's decoder of builtins, if the handler has one.

    Returns:
        An extractor function.
    """
    extract_multipart = partial(
        _extract_multipart,
        body_kwarg_multipart_form_part_limit=body_kwarg.multipart_form_part_limit,
        is_data_optional=is_data_optional,
        decode_builtins=decode_builtins,
        field_definition=field_definition,
    )

    return cast("Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]", extract_multipart)


def create_url_encoded_data_extractor(
    is_data_optional: bool, decode_builtins: DecodeFn | None
) -> Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]:
    """Create extractor for url encoded form-data.

    Args:
        is_data_optional: Boolean dictating whether the field is optional.
        decode_builtins: The data DTO's decoder of builtins, if the handler has one.

    Returns:
        An extractor function.
    """

    async def extract_url_encoded_extractor(
        connection: Request[Any, Any, Any],
    ) -> Any:
        scope_state = ScopeState.from_scope(connection.scope)
        if scope_state.form is Empty:
            scope_state.form = form_values = (  # type: ignore[assignment]
                parse_url_encoded_form_data(await connection.body())
            )
        else:
            form_values = scope_state.form  # type: ignore[assignment]

        if not form_values and is_data_optional:
            return None

        return decode_builtins(form_values, connection) if decode_builtins else form_values

    return cast(
        "Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]", extract_url_encoded_extractor
    )


def create_request_body_extractor(
    field_definition: FieldDefinition, body_kwarg: BodyKwarg, is_data_optional: bool, dto_plan: DTOPlan | None
) -> Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]:
    """Create an extractor decoding a request's body by the media type of its body marker, or
    with its DTO.

    Args:
        field_definition: The declaration of the body.
        body_kwarg: The body marker.
        is_data_optional: Boolean dictating whether the field is optional.
        dto_plan: The handler's DTO plan, if it has one.

    Returns:
        An extractor function.
    """
    media_type = body_kwarg.media_type
    decode_builtins = dto_plan.decode_builtins if dto_plan else None
    decode_bytes = dto_plan.decode_bytes if dto_plan else None

    if media_type == RequestEncodingType.MULTI_PART:
        return create_multipart_extractor(
            field_definition=field_definition,
            body_kwarg=body_kwarg,
            is_data_optional=is_data_optional,
            decode_builtins=decode_builtins,
        )
    if media_type == RequestEncodingType.URL_ENCODED:
        return create_url_encoded_data_extractor(is_data_optional=is_data_optional, decode_builtins=decode_builtins)
    if decode_bytes:
        return create_dto_extractor(decode_bytes=decode_bytes)
    if media_type == RequestEncodingType.MESSAGEPACK:
        return cast("Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]", msgpack_extractor)
    return cast("Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]", json_extractor)


def create_dto_extractor(
    decode_bytes: DecodeFn,
) -> Callable[[ASGIConnection[Any, Any, Any, Any]], Coroutine[Any, Any, Any]]:
    """Create a DTO data extractor.


    Returns:
        An extractor function.
    """

    async def dto_extractor(connection: Request[Any, Any, Any]) -> Any:
        if not (body := await connection.body()):
            return Empty
        return decode_bytes(body, connection)

    return dto_extractor  # type:ignore[return-value]


class RequestParameterExtractor:
    """Read the raw values of request parameters, and the request body, from a connection"""

    __slots__ = ("_body", "_names_by_param_type", "_sequence_query_parameter_names")

    def __init__(self, definitions: Iterable[RequestParameterDefinition], *, dto_plan: DTOPlan | None = None) -> None:
        """Create an extractor of the request parameters ``definitions`` define.

        Args:
            definitions: The request parameters to read
            dto_plan: The DTO plan decoding the body, if there is one
        """
        self._names_by_param_type: dict[ParamType, list[tuple[str, str]]] = {}
        self._body: tuple[str, Callable[[ASGIConnection], Coroutine[Any, Any, Any]]] | None = None
        sequence_query_parameter_names: set[str] = set()
        for definition in definitions:
            marker = definition.marker
            if isinstance(marker, BodyKwarg):
                field_definition = definition.field_definition
                self._body = (
                    definition.key,
                    create_request_body_extractor(
                        field_definition=field_definition,
                        body_kwarg=marker,
                        is_data_optional=field_definition.is_optional,
                        dto_plan=dto_plan,
                    ),
                )
                continue
            # headers are looked up case-insensitively
            name = definition.name.lower() if marker.param_type is ParamType.HEADER else definition.name
            self._names_by_param_type.setdefault(marker.param_type, []).append((definition.key, name))
            if marker.param_type is ParamType.QUERY and definition.field_definition.is_non_string_sequence:
                sequence_query_parameter_names.add(definition.name)
        self._sequence_query_parameter_names = frozenset(sequence_query_parameter_names)

    async def extract(self, connection: ASGIConnection) -> dict[str, Any]:
        """Return the raw value of each request parameter present in the request of
        ``connection``, and the body if the request has one, by key. The body is
        decoded by its media type, or by the DTO.
        """
        raw: dict[str, Any] = {}
        # performance: using dict comprehensions instead of dict.update() with a
        # generator comprehension is a bit faster
        if names := self._names_by_param_type.get(ParamType.QUERY):
            query = parse_query_params(connection, self._sequence_query_parameter_names)
            raw |= {key: query[name] for key, name in names if name in query}

        if names := self._names_by_param_type.get(ParamType.HEADER):
            headers = parse_headers(connection)
            raw |= {key: headers[name] for key, name in names if name in headers}

        if names := self._names_by_param_type.get(ParamType.COOKIE):
            cookies = connection.cookies
            raw |= {key: cookies[name] for key, name in names if name in cookies}

        if names := self._names_by_param_type.get(ParamType.PATH):
            path_params = connection.path_params
            raw |= {key: path_params[name] for key, name in names if name in path_params}

        if self._body is not None:
            key, body_extractor = self._body
            if (body := await body_extractor(connection)) is not Empty:
                raw[key] = body

        return raw
