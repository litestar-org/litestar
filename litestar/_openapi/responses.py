from __future__ import annotations

import contextlib
import re
from copy import copy
from dataclasses import asdict
from http import HTTPStatus
from inspect import Signature
from operator import attrgetter
from typing import TYPE_CHECKING, Any, Iterator

from litestar.enums import MediaType
from litestar.exceptions import HTTPException, ValidationException
from litestar.openapi.spec import OpenAPIResponse
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.header import OpenAPIHeader
from litestar.openapi.spec.media_type import OpenAPIMediaType
from litestar.openapi.spec.schema import Schema
from litestar.response import (
    File,
    Redirect,
    Stream,
    Template,
)
from litestar.response import (
    Response as LitestarResponse,
)
from litestar.response.base import ASGIResponse
from litestar.types.builtin_types import NoneType
from litestar.typing import FieldDefinition
from litestar.utils import get_enum_string_value, get_name

if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.datastructures.cookie import Cookie
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.openapi.spec.responses import Responses


__all__ = (
    "create_additional_responses",
    "create_cookie_schema",
    "create_error_responses",
    "create_responses",
    "create_success_response",
)

CAPITAL_LETTERS_PATTERN = re.compile(r"(?=[A-Z])")


def pascal_case_to_text(string: str) -> str:
    """Given a 'PascalCased' string, return its split form- 'Pascal Cased'."""
    return " ".join(re.split(CAPITAL_LETTERS_PATTERN, string)).strip()


def create_cookie_schema(cookie: Cookie) -> Schema:
    """Given a Cookie instance, return its corresponding OpenAPI schema.

    Args:
        cookie: Cookie

    Returns:
        Schema
    """
    cookie_copy = copy(cookie)
    cookie_copy.value = "<string>"
    value = cookie_copy.to_header(header="")
    return Schema(description=cookie.description or "", example=value)


def create_success_response(  # noqa: C901
    route_handler: HTTPRouteHandler, schema_creator: SchemaCreator
) -> OpenAPIResponse:
    """Create the schema for a success response."""
    field_definition = route_handler.parsed_fn_signature.return_type
    return_annotation = field_definition.annotation
    default_descriptions: dict[Any, str] = {
        Stream: "Stream Response",
        Redirect: "Redirect Response",
        File: "File Download",
    }
    description = (
        route_handler.response_description
        or default_descriptions.get(return_annotation)
        or HTTPStatus(route_handler.status_code).description
    )

    if return_annotation is not Signature.empty and not field_definition.is_subclass_of(
        (NoneType, File, Redirect, Stream, ASGIResponse)
    ):
        media_type = route_handler.media_type

        if return_annotation is Template:
            return_annotation = str
            media_type = media_type or MediaType.HTML

        elif field_definition.is_subclass_of(LitestarResponse):
            return_annotation = field_definition.inner_types[0].annotation if field_definition.inner_types else Any
            media_type = media_type or MediaType.JSON

        if dto := route_handler.resolve_return_dto():
            result = dto.create_openapi_schema(
                field_definition=field_definition, handler_id=route_handler.handler_id, schema_creator=schema_creator
            )
        else:
            result = schema_creator.for_field_definition(FieldDefinition.from_annotation(return_annotation))

        schema = result if isinstance(result, Schema) else schema_creator.schemas[result.value]

        schema.content_encoding = route_handler.content_encoding
        schema.content_media_type = route_handler.content_media_type

        response = OpenAPIResponse(
            content={get_enum_string_value(media_type): OpenAPIMediaType(schema=result)}, description=description
        )

    elif field_definition.is_subclass_of(Redirect):
        response = OpenAPIResponse(
            content=None,
            description=description,
            headers={
                "location": OpenAPIHeader(
                    schema=Schema(type=OpenAPIType.STRING), description="target path for the redirect"
                )
            },
        )

    elif field_definition.is_subclass_of((File, Stream)):
        response = OpenAPIResponse(
            content={
                route_handler.media_type: OpenAPIMediaType(
                    schema=Schema(
                        type=OpenAPIType.STRING,
                        content_encoding=route_handler.content_encoding,
                        content_media_type=route_handler.content_media_type or "application/octet-stream",
                    ),
                )
            },
            description=description,
            headers={
                "content-length": OpenAPIHeader(
                    schema=Schema(type=OpenAPIType.STRING), description="File size in bytes"
                ),
                "last-modified": OpenAPIHeader(
                    schema=Schema(type=OpenAPIType.STRING, format=OpenAPIFormat.DATE_TIME),
                    description="Last modified data-time in RFC 2822 format",
                ),
                "etag": OpenAPIHeader(schema=Schema(type=OpenAPIType.STRING), description="Entity tag"),
            },
        )

    else:
        response = OpenAPIResponse(
            content=None,
            description=description,
        )

    if response.headers is None:
        response.headers = {}

    no_examples_schema_creator = schema_creator.not_generating_examples
    for response_header in route_handler.resolve_response_headers():
        header = OpenAPIHeader()
        for attribute_name, attribute_value in ((k, v) for k, v in asdict(response_header).items() if v is not None):
            if attribute_name == "value":
                header.schema = no_examples_schema_creator.for_field_definition(
                    FieldDefinition.from_annotation(type(attribute_value))
                )
            elif attribute_name != "documentation_only":
                setattr(header, attribute_name, attribute_value)

        response.headers[response_header.name] = header

    if cookies := route_handler.resolve_response_cookies():
        response.headers["Set-Cookie"] = OpenAPIHeader(
            schema=Schema(
                all_of=[create_cookie_schema(cookie=cookie) for cookie in sorted(cookies, key=attrgetter("key"))]
            )
        )

    return response


def create_error_responses(exceptions: list[type[HTTPException]]) -> Iterator[tuple[str, OpenAPIResponse]]:
    """Create the schema for error responses, if any."""
    grouped_exceptions: dict[int, list[type[HTTPException]]] = {}
    for exc in exceptions:
        if not grouped_exceptions.get(exc.status_code):
            grouped_exceptions[exc.status_code] = []
        grouped_exceptions[exc.status_code].append(exc)
    for status_code, exception_group in grouped_exceptions.items():
        exceptions_schemas = []
        group_description: str = ""
        for exc in exception_group:
            example_detail = ""
            if hasattr(exc, "detail") and exc.detail:
                group_description = exc.detail
                example_detail = exc.detail

            if not example_detail:
                with contextlib.suppress(Exception):
                    example_detail = HTTPStatus(status_code).phrase

            exceptions_schemas.append(
                Schema(
                    type=OpenAPIType.OBJECT,
                    required=["detail", "status_code"],
                    properties={
                        "status_code": Schema(type=OpenAPIType.INTEGER),
                        "detail": Schema(type=OpenAPIType.STRING),
                        "extra": Schema(
                            type=[OpenAPIType.NULL, OpenAPIType.OBJECT, OpenAPIType.ARRAY],
                            additional_properties=Schema(),
                        ),
                    },
                    description=pascal_case_to_text(get_name(exc)),
                    examples=[{"status_code": status_code, "detail": example_detail, "extra": {}}],
                )
            )
        if len(exceptions_schemas) > 1:  # noqa: SIM108
            schema = Schema(one_of=exceptions_schemas)
        else:
            schema = exceptions_schemas[0]

        if not group_description:
            with contextlib.suppress(Exception):
                group_description = HTTPStatus(status_code).description

        yield str(status_code), OpenAPIResponse(
            description=group_description,
            content={MediaType.JSON: OpenAPIMediaType(schema=schema)},
        )


def create_additional_responses(
    route_handler: HTTPRouteHandler, schema_creator: SchemaCreator
) -> Iterator[tuple[str, OpenAPIResponse]]:
    """Create the schema for additional responses, if any."""
    if not route_handler.responses:
        return

    schema_creator = copy(schema_creator)
    for status_code, additional_response in route_handler.responses.items():
        schema_creator.generate_examples = additional_response.generate_examples
        schema = schema_creator.for_field_definition(
            FieldDefinition.from_annotation(additional_response.data_container)
        )
        yield str(status_code), OpenAPIResponse(
            description=additional_response.description,
            content={additional_response.media_type: OpenAPIMediaType(schema=schema)},
        )


def create_responses(
    route_handler: HTTPRouteHandler, raises_validation_error: bool, schema_creator: SchemaCreator
) -> Responses | None:
    """Create a Response model embedded in a `Responses` dictionary for the given RouteHandler or return None."""
    responses: Responses = {
        str(route_handler.status_code): create_success_response(route_handler, schema_creator),
    }

    exceptions = list(route_handler.raises or [])
    if raises_validation_error and ValidationException not in exceptions:
        exceptions.append(ValidationException)
    for status_code, response in create_error_responses(exceptions=exceptions):
        responses[status_code] = response

    for status_code, response in create_additional_responses(route_handler, schema_creator):
        responses[status_code] = response

    return responses or None
