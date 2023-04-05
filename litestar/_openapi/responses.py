from __future__ import annotations

import re
from copy import copy
from dataclasses import asdict
from http import HTTPStatus
from inspect import Signature
from operator import attrgetter
from typing import TYPE_CHECKING, Any, Iterator

from typing_extensions import get_args, get_origin

from litestar._openapi.schema_generation import create_schema
from litestar._signature.field import SignatureField
from litestar.enums import MediaType
from litestar.exceptions import HTTPException, ValidationException
from litestar.openapi.spec import OpenAPIResponse
from litestar.openapi.spec.enums import OpenAPIFormat, OpenAPIType
from litestar.openapi.spec.header import OpenAPIHeader
from litestar.openapi.spec.media_type import OpenAPIMediaType
from litestar.openapi.spec.schema import Schema
from litestar.response import Response as LitestarResponse
from litestar.response_containers import File, Redirect, Stream, Template
from litestar.types.builtin_types import NoneType
from litestar.utils import get_enum_string_value, get_name, is_class_and_subclass

if TYPE_CHECKING:
    from litestar.datastructures.cookie import Cookie
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.openapi.spec.responses import Responses
    from litestar.plugins import OpenAPISchemaPluginProtocol


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


def create_cookie_schema(cookie: "Cookie") -> Schema:
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


def create_success_response(
    route_handler: "HTTPRouteHandler",
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, "Schema"],
) -> OpenAPIResponse:
    """Create the schema for a success response."""
    return_annotation = route_handler.parsed_fn_signature.return_type.annotation
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

    if return_annotation not in {Signature.empty, None, NoneType, Redirect, File, Stream}:
        if return_annotation is Template:
            return_annotation = str
            route_handler.media_type = get_enum_string_value(MediaType.HTML)
        elif is_class_and_subclass(get_origin(return_annotation), LitestarResponse):
            return_annotation = get_args(return_annotation)[0] or Any

        result = create_schema(
            field=SignatureField.create(field_type=return_annotation),
            generate_examples=generate_examples,
            plugins=plugins,
            schemas=schemas,
        )

        schema = result if isinstance(result, Schema) else schemas[result.value]

        schema.content_encoding = route_handler.content_encoding
        schema.content_media_type = route_handler.content_media_type

        response = OpenAPIResponse(
            content={
                route_handler.media_type: OpenAPIMediaType(
                    schema=result,
                )
            },
            description=description,
        )

    elif return_annotation is Redirect:
        response = OpenAPIResponse(
            content=None,
            description=description,
            headers={
                "location": OpenAPIHeader(
                    schema=Schema(type=OpenAPIType.STRING), description="target path for the redirect"
                )
            },
        )

    elif return_annotation in (File, Stream):
        response = OpenAPIResponse(
            content={
                route_handler.media_type: OpenAPIMediaType(
                    schema=Schema(
                        type=OpenAPIType.STRING,
                        content_encoding=route_handler.content_encoding or "application/octet-stream",
                        content_media_type=route_handler.content_media_type,
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

    for response_header in route_handler.resolve_response_headers():
        header = OpenAPIHeader()
        for attribute_name, attribute_value in ((k, v) for k, v in asdict(response_header).items() if v is not None):
            if attribute_name == "value":
                header.schema = create_schema(
                    field=SignatureField.create(field_type=type(attribute_value)),
                    generate_examples=False,
                    plugins=plugins,
                    schemas=schemas,
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
        exceptions_schemas = [
            Schema(
                type=OpenAPIType.OBJECT,
                required=["detail", "status_code"],
                properties={
                    "status_code": Schema(type=OpenAPIType.INTEGER),
                    "detail": Schema(type=OpenAPIType.STRING),
                    "extra": Schema(
                        type=[OpenAPIType.NULL, OpenAPIType.OBJECT, OpenAPIType.ARRAY], additional_properties=Schema()
                    ),
                },
                description=pascal_case_to_text(get_name(exc)),
                examples=[{"status_code": status_code, "detail": HTTPStatus(status_code).phrase, "extra": {}}],
            )
            for exc in exception_group
        ]
        if len(exceptions_schemas) > 1:  # noqa: SIM108
            schema = Schema(one_of=exceptions_schemas)
        else:
            schema = exceptions_schemas[0]
        yield str(status_code), OpenAPIResponse(
            description=HTTPStatus(status_code).description,
            content={MediaType.JSON: OpenAPIMediaType(schema=schema)},
        )


def create_additional_responses(
    route_handler: "HTTPRouteHandler",
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, "Schema"],
) -> Iterator[tuple[str, OpenAPIResponse]]:
    """Create the schema for additional responses, if any."""
    if not route_handler.responses:
        return

    for status_code, additional_response in route_handler.responses.items():
        schema = create_schema(
            field=SignatureField.create(field_type=additional_response.data_container),
            generate_examples=additional_response.generate_examples,
            plugins=plugins,
            schemas=schemas,
        )
        yield str(status_code), OpenAPIResponse(
            description=additional_response.description,
            content={additional_response.media_type: OpenAPIMediaType(schema=schema)},
        )


def create_responses(
    route_handler: "HTTPRouteHandler",
    raises_validation_error: bool,
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, "Schema"],
) -> Responses | None:
    """Create a Response model embedded in a `Responses` dictionary for the given RouteHandler or return None."""

    responses: Responses = {
        str(route_handler.status_code): create_success_response(
            generate_examples=generate_examples, plugins=plugins, route_handler=route_handler, schemas=schemas
        ),
    }

    exceptions = list(route_handler.raises or [])
    if raises_validation_error and ValidationException not in exceptions:
        exceptions.append(ValidationException)
    for status_code, response in create_error_responses(exceptions=exceptions):
        responses[status_code] = response

    for status_code, response in create_additional_responses(
        route_handler=route_handler, plugins=plugins, schemas=schemas
    ):
        responses[status_code] = response

    return responses or None
