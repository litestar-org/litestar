from __future__ import annotations

import contextlib
import re
from copy import copy
from dataclasses import asdict, replace
from http import HTTPStatus
from operator import attrgetter
from typing import TYPE_CHECKING, Any

from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.schema_generation.utils import get_formatted_examples
from litestar._openapi.utils import supports_openapi_3_2
from litestar.enums import MediaType
from litestar.handlers.http_handlers._utils import is_empty_response_annotation
from litestar.openapi.spec import Example, OpenAPIResponse, Reference
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
from litestar.response.sse import ServerSentEvent
from litestar.types.builtin_types import NoneType
from litestar.typing import FieldDefinition
from litestar.utils import get_enum_string_value, get_name

if TYPE_CHECKING:
    from collections.abc import Collection, Iterator

    from litestar._openapi.datastructures import OpenAPIContext
    from litestar._openapi.operation import OperationDescription
    from litestar.datastructures.cookie import Cookie
    from litestar.exceptions import HTTPException
    from litestar.openapi.datastructures import ResponseSpec
    from litestar.openapi.spec.responses import Responses


__all__ = ("ResponseFactory",)

SEQUENTIAL_MEDIA_TYPES = frozenset({"application/jsonl", "application/x-ndjson", "application/json-seq"})

WORD_BOUNDARY_PATTERN = re.compile(
    r"""
    (?<=[a-z0-9])(?=[A-Z])      # a lowercase letter or digit, followed by an uppercase letter
    |
    (?<=[A-Z])(?=[A-Z][a-z])    # an uppercase run, followed by a new capitalized word
    """,
    re.VERBOSE,
)


def pascal_case_to_text(string: str) -> str:
    """Given a 'PascalCased' string, return its split form- 'Pascal Cased'."""
    return " ".join(re.split(WORD_BOUNDARY_PATTERN, string)).strip()


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
    return Schema(description=cookie.description or "", examples=[value])


class ResponseFactory:
    """Factory for creating a Response instance for a given route handler."""

    def __init__(self, context: OpenAPIContext, operation: OperationDescription) -> None:
        """Initialize the factory.

        Args:
            context: An OpenAPIContext instance.
            operation: The operation to create responses for.
        """
        self.context = context
        self.operation = operation
        self.response = operation.response
        self.field_definition = operation.response.return_type
        self.schema_creator = SchemaCreator.from_openapi_context(
            context, prefer_alias=False, signature_namespace=operation.signature_namespace
        )

    def create_responses(self) -> Responses | None:
        """Create the schema for responses, if any.

        Returns:
            Responses
        """
        responses: Responses = {
            str(self.response.status_code): self.create_success_response(),
        }

        overridden = {int(status_code) for status_code in self.operation.additional_responses}
        for status_code, response in create_error_responses(
            list(self.operation.raises), self.context.openapi_config.error_response, self.schema_creator, overridden
        ):
            responses[status_code] = response

        for status_code, response in self.create_additional_responses():
            responses[status_code] = response

        if not self.operation.allows_response_body:
            responses = {
                status_code: replace(response, content=None) if isinstance(response, OpenAPIResponse) else response
                for status_code, response in responses.items()
            }
        return responses or None

    def create_description(self) -> str:
        """Create the description for a success response."""
        default_descriptions: dict[Any, str] = {
            Stream: "Stream Response",
            Redirect: "Redirect Response",
            File: "File Download",
        }
        return (
            self.response.description
            or default_descriptions.get(self.field_definition.annotation)
            or HTTPStatus(self.response.status_code).description
        )

    def create_success_response(self) -> OpenAPIResponse:
        """Create the schema for a success response."""
        if self.field_definition.is_subclass_of((NoneType, ASGIResponse)) or (
            not self.response.allows_body and is_empty_response_annotation(self.field_definition)
        ):
            response = OpenAPIResponse(content=None, description=self.create_description())
        elif self.field_definition.is_subclass_of(Redirect):
            response = self.create_redirect_response()
        elif self.field_definition.is_subclass_of(File):
            response = self.create_file_response()
        elif self.field_definition.is_subclass_of(ServerSentEvent):
            response = self.create_server_sent_event_response()
        else:
            media_type = self.response.media_type

            if dto := self.response.dto:
                result = dto.create_openapi_schema(
                    field_definition=self.field_definition,
                    handler_id=self.operation.handler_id,
                    schema_creator=self.schema_creator,
                )
            else:
                if self.field_definition.is_subclass_of(Template):
                    field_def = FieldDefinition.from_annotation(str)
                    media_type = media_type or MediaType.HTML
                elif self.field_definition.is_subclass_of(LitestarResponse):
                    field_def = (
                        self.field_definition.inner_types[0]
                        if self.field_definition.inner_types
                        else FieldDefinition.from_annotation(Any)
                    )
                    media_type = media_type or MediaType.JSON
                else:
                    field_def = self.field_definition

                result = self.schema_creator.for_field_definition(field_def)

            content_encoding = self.response.content_encoding
            content_media_type = self.response.content_media_type
            if isinstance(result, Reference):
                if content_encoding or content_media_type:
                    result = Schema(
                        all_of=[result], content_encoding=content_encoding, content_media_type=content_media_type
                    )
            else:
                result.content_encoding = content_encoding
                result.content_media_type = content_media_type
            media_type = get_enum_string_value(media_type or MediaType.JSON)
            is_item_stream = (
                self.field_definition.is_subclass_of(Stream)
                and media_type in SEQUENTIAL_MEDIA_TYPES
                and supports_openapi_3_2(self.context.openapi_config.openapi_version)
            )
            response = OpenAPIResponse(
                content={
                    media_type: OpenAPIMediaType(item_schema=result)
                    if is_item_stream
                    else OpenAPIMediaType(schema=result)
                },
                description=self.create_description(),
            )
        self.set_success_response_headers(response)
        return response

    def create_redirect_response(self) -> OpenAPIResponse:
        """Create the schema for a redirect response."""
        return OpenAPIResponse(
            content=None,
            description=self.create_description(),
            headers={
                "location": OpenAPIHeader(
                    schema=Schema(type=OpenAPIType.STRING), description="target path for the redirect"
                )
            },
        )

    def create_server_sent_event_response(self) -> OpenAPIResponse:
        """Create the schema for a server-sent events response."""
        if supports_openapi_3_2(self.context.openapi_config.openapi_version):
            media_type = OpenAPIMediaType(
                item_schema=Schema(
                    type=OpenAPIType.OBJECT,
                    properties={
                        "data": Schema(type=OpenAPIType.STRING),
                        "event": Schema(type=OpenAPIType.STRING),
                        "id": Schema(type=OpenAPIType.STRING),
                        "retry": Schema(type=OpenAPIType.INTEGER, minimum=0),
                    },
                )
            )
        else:
            media_type = OpenAPIMediaType(schema=Schema(type=OpenAPIType.STRING))
        return OpenAPIResponse(content={"text/event-stream": media_type}, description=self.create_description())

    def create_file_response(self) -> OpenAPIResponse:
        """Create the schema for a file/stream response."""
        return OpenAPIResponse(
            content={
                get_enum_string_value(self.response.media_type or "application/octet-stream"): OpenAPIMediaType(
                    schema=Schema(
                        type=OpenAPIType.STRING,
                        content_encoding=self.response.content_encoding,
                        content_media_type=self.response.content_media_type or "application/octet-stream",
                    ),
                )
            },
            description=self.create_description(),
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

    def set_success_response_headers(self, response: OpenAPIResponse) -> None:
        """Set the schema for success response headers, if any."""

        if response.headers is None:
            response.headers = {}

        schema_creator = self.schema_creator.not_generating_examples

        for response_header in self.response.headers:
            header = OpenAPIHeader()
            for attribute_name, attribute_value in (
                (k, v) for k, v in asdict(response_header).items() if v is not None
            ):
                if attribute_name == "value":
                    header.schema = schema_creator.for_field_definition(
                        FieldDefinition.from_annotation(type(attribute_value))
                    )
                elif attribute_name != "documentation_only":
                    setattr(header, attribute_name, attribute_value)
            if header.schema is None and header.content is None:
                header.schema = Schema(type=OpenAPIType.STRING)

            response.headers[response_header.name] = header

        if cookies := self.response.cookies:
            response.headers["Set-Cookie"] = OpenAPIHeader(
                schema=Schema(
                    all_of=[create_cookie_schema(cookie=cookie) for cookie in sorted(cookies, key=attrgetter("key"))]
                )
            )

    def create_additional_responses(self) -> Iterator[tuple[str, OpenAPIResponse]]:
        """Create the schema for additional responses, if any."""
        for status_code, additional_response in self.operation.additional_responses.items():
            schema_creator = SchemaCreator.from_openapi_context(
                self.context,
                prefer_alias=False,
                generate_examples=additional_response.generate_examples,
                signature_namespace=self.operation.signature_namespace,
            )
            field_def = FieldDefinition.from_annotation(additional_response.data_container)

            examples: dict[str, Example | Reference] | None = (
                dict(get_formatted_examples(field_def, additional_response.examples))
                if additional_response.examples
                else None
            )

            content: dict[str, OpenAPIMediaType] | None
            if additional_response.data_container is not None:
                schema = schema_creator.for_field_definition(field_def)
                media_type = additional_response.media_type
                content = {
                    get_enum_string_value(media_type)
                    if not isinstance(media_type, str)
                    else media_type: OpenAPIMediaType(schema=schema, examples=examples)
                }
            else:
                content = None

            yield (
                str(status_code),
                OpenAPIResponse(
                    description=additional_response.description,
                    content=content,
                ),
            )


def create_error_responses(
    exceptions: list[type[HTTPException]],
    response_spec: ResponseSpec | None = None,
    schema_creator: SchemaCreator | None = None,
    overridden: Collection[int] = (),
) -> Iterator[tuple[str, OpenAPIResponse]]:
    """Create the schema for error responses, if any.

    Args:
        exceptions: The exceptions to document.
        response_spec: Describes the content of every error response. If ``None``, the content of Litestar's default
            exception response is documented.
        schema_creator: The schema creator used to generate the schema of ``response_spec``.
        overridden: Status codes whose response is replaced afterwards. No schema is generated for them from
            ``response_spec``.
    """
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
        content: dict[str, OpenAPIMediaType] | None
        if response_spec is None or schema_creator is None:
            content = {
                MediaType.JSON: OpenAPIMediaType(
                    schema=Schema(one_of=exceptions_schemas) if len(exceptions_schemas) > 1 else exceptions_schemas[0]
                )
            }
        elif response_spec.data_container is None or status_code in overridden:
            content = None
        else:
            field_definition = FieldDefinition.from_annotation(response_spec.data_container)
            if not response_spec.generate_examples:
                schema_creator = schema_creator.not_generating_examples
            content = {
                get_enum_string_value(response_spec.media_type): OpenAPIMediaType(
                    schema=schema_creator.for_field_definition(field_definition),
                    examples=dict(get_formatted_examples(field_definition, response_spec.examples))
                    if response_spec.examples
                    else None,
                )
            }

        if not group_description:
            with contextlib.suppress(Exception):
                group_description = HTTPStatus(status_code).description

        yield str(status_code), OpenAPIResponse(description=group_description, content=content)
