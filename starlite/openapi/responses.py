from http import HTTPStatus
from inspect import Signature
from typing import Callable, Dict, Iterator, List, Optional, Tuple, Type, Union, cast

from openapi_schema_pydantic import Header
from openapi_schema_pydantic import MediaType as OpenAPISchemaMediaType
from openapi_schema_pydantic import Response, Responses, Schema
from pydantic import BaseModel
from pydantic_factories.protocols import DataclassProtocol
from starlette.routing import get_name

from starlite.enums import MediaType
from starlite.exceptions import HTTPException, ValidationException
from starlite.handlers import RouteHandler
from starlite.openapi.enums import OpenAPIType
from starlite.openapi.schema import create_schema
from starlite.openapi.utils import get_media_type, pascal_case_to_text
from starlite.utils.model import create_parsed_model_field


def create_success_response(
    route_handler: RouteHandler,
    default_response_headers: Optional[Union[Type[DataclassProtocol], Type[BaseModel]]],
    generate_examples: bool,
):
    """
    Creates the schema for a success response
    """
    signature = Signature.from_callable(cast(Callable, route_handler.fn))
    if signature.return_annotation not in [signature.empty, None]:
        as_parsed_model_field = create_parsed_model_field(signature.return_annotation)
        response = Response(
            content={
                get_media_type(route_handler): OpenAPISchemaMediaType(
                    media_type_schema=create_schema(field=as_parsed_model_field, generate_examples=generate_examples)
                )
            },
            description=HTTPStatus(cast(int, route_handler.status_code)).description,
        )
    else:
        response = Response(
            content=None,
            description=HTTPStatus(cast(int, route_handler.status_code)).description,
        )
    response_headers = route_handler.response_headers or default_response_headers
    if response_headers:
        response.headers = {}
        for key, value in response_headers.__fields__.items():
            response.headers[key.replace("_", "-")] = Header(
                param_schema=create_schema(field=value, generate_examples=generate_examples)
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
    default_response_headers: Optional[Union[Type[DataclassProtocol], Type[BaseModel]]],
    generate_examples: bool,
) -> Optional[Responses]:
    """
    Create a Response model embedded in a responses dictionary for the given RouteHandler or return None
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
