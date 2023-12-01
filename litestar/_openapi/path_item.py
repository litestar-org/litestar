from __future__ import annotations

from functools import cached_property
from inspect import cleandoc
from typing import TYPE_CHECKING

from litestar._openapi.parameters import ParameterFactory
from litestar._openapi.request_body import RequestBodyFactory
from litestar._openapi.responses import create_responses
from litestar._openapi.schema_generation import SchemaCreator
from litestar._openapi.utils import SEPARATORS_CLEANUP_PATTERN
from litestar.openapi.spec import PathItem
from litestar.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from litestar._openapi.factory import OpenAPIContext
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.routes import HTTPRoute

__all__ = ("PathItemFactory",)


class PathItemFactory:
    def __init__(self, openapi_context: OpenAPIContext) -> None:
        self.context = openapi_context
        self.request_body_factory = RequestBodyFactory(self.context)

    @cached_property
    def response_schema_creator(self) -> SchemaCreator:
        return SchemaCreator(
            generate_examples=self.context.openapi_config.create_examples,
            plugins=self.context.plugins,
            schemas=self.context.schemas,
            prefer_alias=False,
        )

    def create_path_item(self, route: HTTPRoute) -> tuple[PathItem, list[str]]:
        """Create a PathItem for the given route parsing all http_methods into Operation Models.

        Args:
            route: An HTTPRoute instance.

        Returns:
            A tuple containing the path item and a list of operation ids.
        """
        path_item = PathItem()
        operation_ids: list[str] = []

        for http_method, handler_tuple in route.route_handler_map.items():
            route_handler, _ = handler_tuple

            if route_handler.resolve_include_in_schema():
                parameter_factory = ParameterFactory(self.context, route_handler, route.path_parameters)
                parameters = parameter_factory.create_parameters_for_handler()
                signature_fields = route_handler.signature_model._fields
                raises_validation_error = bool("data" in signature_fields or path_item.parameters or parameters)

                request_body = None
                if data_field := signature_fields.get("data"):
                    request_body = self.request_body_factory.create_request_body(
                        route_handler=route_handler, field_definition=data_field
                    )

                if isinstance(route_handler.operation_id, str):
                    operation_id = route_handler.operation_id
                elif callable(route_handler.operation_id):
                    operation_id = route_handler.operation_id(route_handler, http_method, route.path_components)
                else:
                    operation_id = self.context.openapi_config.operation_id_creator(
                        route_handler, http_method, route.path_components
                    )

                operation = route_handler.operation_class(
                    operation_id=operation_id,
                    tags=route_handler.resolve_tags() or None,
                    summary=route_handler.summary
                    or SEPARATORS_CLEANUP_PATTERN.sub("", route_handler.handler_name.title()),
                    description=self.get_description_for_handler(route_handler),
                    deprecated=route_handler.deprecated,
                    responses=create_responses(
                        route_handler=route_handler,
                        raises_validation_error=raises_validation_error,
                        schema_creator=self.response_schema_creator,
                    ),
                    request_body=request_body,
                    parameters=parameters or None,  # type: ignore[arg-type]
                    security=route_handler.resolve_security() or None,
                )
                operation_ids.append(operation_id)
                setattr(path_item, http_method.lower(), operation)

        return path_item, operation_ids

    def get_description_for_handler(self, route_handler: HTTPRouteHandler) -> str | None:
        """Produce the operation description for a route handler, either by using the description value if provided,

        or the docstring - if config is enabled.

        Args:
            route_handler: A route handler instance.

        Returns:
            An optional description string
        """
        handler_description = route_handler.description
        if handler_description is None and self.context.openapi_config.use_handler_docstrings:
            fn = unwrap_partial(route_handler.fn)
            return cleandoc(fn.__doc__) if fn.__doc__ else None
        return handler_description
