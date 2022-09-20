from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, cast

from pydantic_openapi_schema.v3_1_0.operation import Operation
from pydantic_openapi_schema.v3_1_0.path_item import PathItem
from starlette.routing import get_name

from starlite.openapi.parameters import create_parameter_for_handler
from starlite.openapi.request_body import create_request_body
from starlite.openapi.responses import create_responses

if TYPE_CHECKING:
    from pydantic import BaseModel
    from pydantic_openapi_schema.v3_1_0 import SecurityRequirement

    from starlite.handlers import HTTPRouteHandler
    from starlite.plugins.base import PluginProtocol
    from starlite.routes import HTTPRoute
    from starlite.types import AnyCallable


def get_description_for_handler(route_handler: "HTTPRouteHandler", use_handler_docstrings: bool) -> Optional[str]:
    """Produces the operation description for a route handler, either by using the description value if provided, or the docstring - if config is enabled.

    Args:
        route_handler: A route handler instance.
        use_handler_docstrings: If `True` and `route_handler.description` is `None` returns docstring of wrapped
            handler function.

    Returns:
        An optional description string
    """
    handler_description = route_handler.description
    if handler_description is None and use_handler_docstrings:
        return route_handler.fn.__doc__
    return handler_description


def extract_layered_values(
    route_handler: "HTTPRouteHandler",
) -> Tuple[Optional[List[str]], Optional[List[Dict[str, List[str]]]]]:
    """Extracts the tags and security values from the route handler layers.

    Args:
        route_handler: A Route Handler instance.

    Returns:
        A tuple of optional lists.
    """
    tags: List[str] = []
    security: List["SecurityRequirement"] = []
    for layer in route_handler.ownership_layers:
        if layer.tags:
            tags.extend(layer.tags)
        if layer.security:
            security.extend(layer.security)
    return list(set(tags)) if tags else None, security or None


def create_path_item(
    route: "HTTPRoute", create_examples: bool, plugins: List["PluginProtocol"], use_handler_docstrings: bool
) -> PathItem:
    """Create a PathItem model for the given route parsing all http_methods
    into Operation Models."""
    path_item = PathItem()
    for http_method, handler_tuple in route.route_handler_map.items():
        route_handler, _ = handler_tuple
        if route_handler.include_in_schema:
            handler_fields = cast("BaseModel", route_handler.signature_model).__fields__
            parameters = (
                create_parameter_for_handler(
                    route_handler=route_handler,
                    handler_fields=handler_fields,
                    path_parameters=route.path_parameters,
                    generate_examples=create_examples,
                )
                or None
            )
            raises_validation_error = bool("data" in handler_fields or path_item.parameters or parameters)
            handler_name = get_name(cast("AnyCallable", route_handler.fn)).replace("_", " ").title()
            request_body = None
            if "data" in handler_fields:
                request_body = create_request_body(
                    field=handler_fields["data"], generate_examples=create_examples, plugins=plugins
                )

            tags, security = extract_layered_values(route_handler)
            operation = Operation(
                operationId=route_handler.operation_id or handler_name,
                tags=tags,
                summary=route_handler.summary,
                description=get_description_for_handler(route_handler, use_handler_docstrings),
                deprecated=route_handler.deprecated,
                responses=create_responses(
                    route_handler=route_handler,
                    raises_validation_error=raises_validation_error,
                    generate_examples=create_examples,
                    plugins=plugins,
                ),
                requestBody=request_body,
                parameters=parameters,  # type: ignore[arg-type]
                security=security,
            )
            setattr(path_item, http_method.lower(), operation)
    return path_item
