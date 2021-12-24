from http import HTTPStatus
from inspect import Signature
from typing import Dict, Iterator, List, Optional, Tuple, Type, Union, cast

from openapi_schema_pydantic import Header
from openapi_schema_pydantic import MediaType as OpenAPISchemaMediaType
from openapi_schema_pydantic import Response, Responses, Schema
from pydantic import BaseModel
from pydantic.typing import AnyCallable
from starlette.responses import RedirectResponse
from starlette.routing import get_name

from starlite.enums import MediaType
from starlite.exceptions import HTTPException, ValidationException
from starlite.handlers import RouteHandler
from starlite.openapi.enums import OpenAPIType
from starlite.openapi.schema import create_schema
from starlite.openapi.utils import pascal_case_to_text
from starlite.types import FileData
from starlite.utils.model import create_parsed_model_field


def create_success_response(
    route_handler: RouteHandler,
    default_response_headers: Optional[Union[Type[BaseModel], BaseModel]],
    generate_examples: bool,
) -> Response:
    """
    Creates the schema for a success response
    """

    signature = Signature.from_callable(cast(AnyCallable, route_handler.fn))
    is_redirect = route_handler.response_class and issubclass(route_handler.response_class, RedirectResponse)
    is_file = signature.return_annotation is FileData
    if signature.return_annotation not in [signature.empty, None, FileData] and not is_redirect:
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
            description=HTTPStatus(cast(int, route_handler.status_code)).description,
        )
    elif is_redirect:
        response = Response(
            content=None,
            description="Redirect Response",
        )
    elif is_file:
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
            description="File Download",
        )
    else:
        response = Response(
            content=None,
            description=HTTPStatus(cast(int, route_handler.status_code)).description,
        )
    response_headers = route_handler.response_headers or default_response_headers
    response.headers = {}
    if response_headers:
        for key, value in (
            response_headers.__class__ if isinstance(response_headers, BaseModel) else response_headers
        ).__fields__.items():
            response.headers[key.replace("_", "-")] = Header(
                param_schema=create_schema(field=value, generate_examples=generate_examples)
            )
    if is_redirect and not response.headers.get("location"):
        response.headers["location"] = Header(
            param_schema=Schema(type=OpenAPIType.STRING), description="target path for the redirect"
        )
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
    route_handler: RouteHandler,
    raises_validation_error: bool,
    default_response_headers: Optional[Union[Type[BaseModel], BaseModel]],
    generate_examples: bool,
) -> Optional[Responses]:
    """
    Create a Response model embedded in a `Responses` dictionary for the given RouteHandler or return None
    """
    responses: Responses = {
        str(route_handler.status_code): create_success_response(
            route_handler=route_handler,
            default_response_headers=default_response_headers,
            generate_examples=generate_examples,
        )
    }
    exceptions = route_handler.raises or []
    if raises_validation_error and ValidationException not in exceptions:
        exceptions.append(ValidationException)
    for status_code, response in create_error_responses(exceptions=exceptions):
        responses[status_code] = response
    return responses or None
