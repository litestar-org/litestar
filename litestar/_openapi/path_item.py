from __future__ import annotations

from inspect import cleandoc
from typing import TYPE_CHECKING, Iterable

from litestar._openapi.parameters import create_parameter_for_handler
from litestar._openapi.request_body import create_request_body
from litestar._openapi.responses import create_responses
from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.utils import SEPARATORS_CLEANUP_PATTERN
from litestar.openapi.spec.path_item import PathItem
from litestar.utils.helpers import unwrap_partial

__all__ = ("create_path_item", "extract_layered_values", "get_description_for_handler")

if TYPE_CHECKING:
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.openapi.spec import Schema, SecurityRequirement
    from litestar.plugins import OpenAPISchemaPluginProtocol
    from litestar.routes import HTTPRoute
    from litestar.types.callable_types import OperationIDCreator


def get_description_for_handler(route_handler: HTTPRouteHandler, use_handler_docstrings: bool) -> str | None:
    """Produce the operation description for a route handler, either by using the description value if provided,

    or the docstring - if config is enabled.

    Args:
        route_handler: A route handler instance.
        use_handler_docstrings: If ``True`` and `route_handler.description`` is ``None` returns docstring of wrapped
            handler function.

    Returns:
        An optional description string
    """
    handler_description = route_handler.description
    if handler_description is None and use_handler_docstrings:
        fn = unwrap_partial(route_handler.fn.value)
        return cleandoc(fn.__doc__) if fn.__doc__ else None
    return handler_description


def extract_layered_values(
    route_handler: HTTPRouteHandler,
) -> tuple[list[str] | None, list[dict[str, list[str]]] | None]:
    """Extract the tags and security values from the route handler layers.

    Args:
        route_handler: A Route Handler instance.

    Returns:
        A tuple of optional lists.
    """
    tags: list[str] = []
    security: list[SecurityRequirement] = []
    for layer in route_handler.ownership_layers:
        if layer.tags:
            tags.extend(layer.tags)
        if layer.security:
            security.extend(layer.security)
    return sorted(set(tags)) if tags else None, security or None


def create_path_item(
    create_examples: bool,
    operation_id_creator: OperationIDCreator,
    plugins: Iterable[OpenAPISchemaPluginProtocol],
    route: HTTPRoute,
    schemas: dict[str, Schema],
    use_handler_docstrings: bool,
) -> tuple[PathItem, list[str]]:
    """Create a PathItem for the given route parsing all http_methods into Operation Models.

    Args:
        create_examples: Whether to auto-generate examples.
        operation_id_creator: A function to generate operation ids.
        plugins: A list of plugins.
        route: An HTTPRoute instance.
        schemas: A mapping of schemas.
        use_handler_docstrings: Whether to use the handler docstring.

    Returns:
        A tuple containing the path item and a list of operation ids.
    """
    path_item = PathItem()
    operation_ids: list[str] = []

    request_schema_creator = SchemaCreator(create_examples, plugins, schemas, prefer_alias=True)
    response_schema_creator = SchemaCreator(create_examples, plugins, schemas, prefer_alias=False)
    for http_method, handler_tuple in route.route_handler_map.items():
        route_handler, _ = handler_tuple

        if route_handler.resolve_include_in_schema():
            handler_fields = route_handler.signature_model._fields if route_handler.signature_model else {}
            parameters = (
                create_parameter_for_handler(
                    route_handler=route_handler,
                    handler_fields=handler_fields,
                    path_parameters=route.path_parameters,
                    schema_creator=request_schema_creator,
                )
                or None
            )
            raises_validation_error = bool("data" in handler_fields or path_item.parameters or parameters)

            request_body = None
            if "data" in handler_fields:
                request_body = create_request_body(
                    route_handler=route_handler,
                    field_definition=handler_fields["data"],
                    schema_creator=request_schema_creator,
                )

            if isinstance(route_handler.operation_id, str):
                operation_id = route_handler.operation_id
            elif callable(route_handler.operation_id):
                operation_id = route_handler.operation_id(route_handler, http_method, route.path_components)
            else:
                operation_id = operation_id_creator(route_handler, http_method, route.path_components)

            tags, security = extract_layered_values(route_handler)
            operation = route_handler.operation_class(
                operation_id=operation_id,
                tags=tags,
                summary=route_handler.summary or SEPARATORS_CLEANUP_PATTERN.sub("", route_handler.handler_name.title()),
                description=get_description_for_handler(route_handler, use_handler_docstrings),
                deprecated=route_handler.deprecated,
                responses=create_responses(
                    route_handler=route_handler,
                    raises_validation_error=raises_validation_error,
                    schema_creator=response_schema_creator,
                ),
                request_body=request_body,
                parameters=parameters,  # type: ignore[arg-type]
                security=security,
            )
            operation_ids.append(operation_id)
            setattr(path_item, http_method.lower(), operation)

    return path_item, operation_ids
