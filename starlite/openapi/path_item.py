from typing import TYPE_CHECKING, cast

from openapi_schema_pydantic import Operation, PathItem
from pydantic import BaseModel
from pydantic.typing import AnyCallable
from starlette.routing import get_name

from starlite.openapi.parameters import create_parameters
from starlite.openapi.request_body import create_request_body
from starlite.openapi.responses import create_responses

if TYPE_CHECKING:  # pragma: no cover
    from starlite.routing import HTTPRoute


def create_path_item(route: "HTTPRoute", create_examples: bool) -> PathItem:
    """
    Create a PathItem model for the given route parsing all http_methods into Operation Models
    """
    path_item = PathItem()
    for http_method, route_handler in route.route_handler_map.items():
        if route_handler.include_in_schema:
            handler_fields = cast(BaseModel, route_handler.signature_model).__fields__
            parameters = (
                create_parameters(
                    route_handler=route_handler,
                    handler_fields=handler_fields,
                    path_parameters=route.path_parameters,
                    generate_examples=create_examples,
                )
                or None
            )
            raises_validation_error = bool("data" in handler_fields or path_item.parameters or parameters)
            handler_name = get_name(cast(AnyCallable, route_handler.fn))
            request_body = None
            if "data" in handler_fields:
                request_body = create_request_body(field=handler_fields["data"], generate_examples=create_examples)
            operation = Operation(
                operationId=route_handler.operation_id or handler_name,
                tags=route_handler.tags,
                summary=route_handler.summary,
                description=route_handler.description,
                deprecated=route_handler.deprecated,
                responses=create_responses(
                    route_handler=route_handler,
                    raises_validation_error=raises_validation_error,
                    generate_examples=create_examples,
                ),
                requestBody=request_body,
                parameters=parameters,
            )
            setattr(path_item, http_method, operation)
    return path_item
