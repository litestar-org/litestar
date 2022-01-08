from http import HTTPStatus
from inspect import Signature
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, cast

from openapi_schema_pydantic import Header
from openapi_schema_pydantic import MediaType as OpenAPISchemaMediaType
from openapi_schema_pydantic import Response, Responses, Schema
from pydantic.typing import AnyCallable
from starlette.routing import get_name

from starlite.enums import MediaType
from starlite.exceptions import HTTPException, ValidationException
from starlite.handlers import HTTPRouteHandler
from starlite.openapi.enums import OpenAPIFormat, OpenAPIType
from starlite.openapi.schema import create_schema
from starlite.openapi.utils import pascal_case_to_text
from starlite.types import File, Redirect, Stream
from starlite.utils.model import create_parsed_model_field


def create_success_response(
    route_handler: HTTPRouteHandler,
    generate_examples: bool,
) -> Response:
    """
    Creates the schema for a success response
    """

    signature = Signature.from_callable(cast(AnyCallable, route_handler.fn))
    default_descriptions: Dict[Any, str] = {
        Stream: "Stream Response",
        Redirect: "Redirect Response",
        File: "File Download",
    }
    description = (
        route_handler.response_description
        or default_descriptions.get(signature.return_annotation)
        or HTTPStatus(cast(int, route_handler.status_code)).description
    )
    if signature.return_annotation not in [signature.empty, None, Redirect, File, Stream]:
        as_parsed_model_field = create_parsed_model_field(signature.return_annotation)
        schema = create_schema(field=as_parsed_model_field, generate_examples=generate_examples)
        schema.contentEncoding = route_handler.content_encoding
        schema.contentMediaType = route_handler.content_media_type
        response = Response(
            content={
                route_handler.media_type: OpenAPISchemaMediaType(
                    media_type_schema=schema,
                )
            },
            description=description,
        )
    elif signature.return_annotation is Redirect:
        response = Response(
            content=None,
            description=description,
            headers={
                "location": Header(
                    param_schema=Schema(type=OpenAPIType.STRING), description="target path for the redirect"
                )
            },
        )
    elif signature.return_annotation in [File, Stream]:
        response = Response(
            content={
                route_handler.media_type: OpenAPISchemaMediaType(
                    media_type_schema=Schema(
                        type=OpenAPIType.STRING,
                        contentEncoding=route_handler.content_encoding or "application/octet-stream",
                        contentMediaType=route_handler.content_media_type,
                    ),
                )
            },
            description=description,
            headers={
                "content-length": Header(
                    param_schema=Schema(type=OpenAPIType.STRING), description="File size in bytes"
                ),
                "last-modified": Header(
                    param_schema=Schema(type=OpenAPIType.STRING, schema_format=OpenAPIFormat.DATE_TIME),
                    description="Last modified data-time in RFC 2822 format",
                ),
                "etag": Header(param_schema=Schema(type=OpenAPIType.STRING), description="Entity tag"),
            },
        )
    else:
        response = Response(
            content=None,
            description=description,
        )
    if response.headers is None:
        response.headers = {}
    for key, value in route_handler.resolve_response_headers().items():
        header = Header()
        for attribute_name, attribute_value in value.dict(exclude_none=True).items():
            if attribute_name == "value":
                model_field = create_parsed_model_field(type(attribute_value))
                header.param_schema = create_schema(field=model_field, generate_examples=False)
            else:
                setattr(header, attribute_name, attribute_value)
        response.headers[key] = header
    return response


def create_error_responses(exceptions: List[Type[HTTPException]]) -> Iterator[Tuple[str, Response]]:
    """
    Creates the schema for error responses, if any
    """
    grouped_exceptions: Dict[int, List[Type[HTTPException]]] = {}
    for exc in exceptions:
        if not grouped_exceptions.get(exc.status_code):
            grouped_exceptions[exc.status_code] = []
        grouped_exceptions[exc.status_code].append(exc)
    for status_code, exception_group in grouped_exceptions.items():
        exceptions_schemas = [
            Schema(
                type=OpenAPIType.OBJECT,
                required=["detail", "status_code"],
                properties=dict(
                    status_code=Schema(type=OpenAPIType.INTEGER),
                    detail=Schema(type=OpenAPIType.STRING),
                    extra=Schema(type=OpenAPIType.OBJECT, additionalProperties=Schema()),
                ),
                description=pascal_case_to_text(get_name(exc)),
                examples=[{"status_code": status_code, "detail": HTTPStatus(status_code).phrase, "extra": {}}],
            )
            for exc in exception_group
        ]
        if len(exceptions_schemas) > 1:
            schema = Schema(oneOf=exceptions_schemas)
        else:
            schema = exceptions_schemas[0]
        yield str(status_code), Response(
            description=HTTPStatus(status_code).description,
            content={MediaType.JSON: OpenAPISchemaMediaType(media_type_schema=schema)},
        )


def create_responses(
    route_handler: HTTPRouteHandler,
    raises_validation_error: bool,
    generate_examples: bool,
) -> Optional[Responses]:
    """
    Create a Response model embedded in a `Responses` dictionary for the given RouteHandler or return None
    """
    responses: Responses = {
        str(route_handler.status_code): create_success_response(
            route_handler=route_handler,
            generate_examples=generate_examples,
        )
    }
    exceptions = route_handler.raises or []
    if raises_validation_error and ValidationException not in exceptions:
        exceptions.append(ValidationException)
    for status_code, response in create_error_responses(exceptions=exceptions):
        responses[status_code] = response
    return responses or None
