from __future__ import annotations

from inspect import cleandoc
from typing import TYPE_CHECKING

from litestar._openapi.parameters import ParameterFactory
from litestar._openapi.request_body import RequestBodyFactory
from litestar._openapi.responses import ResponseFactory
from litestar._openapi.utils import SEPARATORS_CLEANUP_PATTERN
from litestar.enums import HttpMethod
from litestar.openapi.spec import Operation, PathItem
from litestar.utils.helpers import unwrap_partial

if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar.handlers.http_handlers import HTTPRouteHandler
    from litestar.routes import HTTPRoute

__all__ = ("PathItemFactory",)


class PathItemFactory:
    def __init__(self, openapi_context: OpenAPIContext, route: HTTPRoute) -> None:
        self.context = openapi_context
        self.route = route
        self._path_item = PathItem()

    def create_path_item(self) -> PathItem:
        """Create a PathItem for the given route parsing all http_methods into Operation Models.

        Returns:
            A PathItem instance.
        """
        for http_method, handler_tuple in self.route.route_handler_map.items():
            route_handler, _ = handler_tuple

            if not route_handler.resolve_include_in_schema():
                continue

            operation = self.create_operation_for_handler_method(route_handler, HttpMethod(http_method))

            setattr(self._path_item, http_method.lower(), operation)

        return self._path_item

    def create_operation_for_handler_method(
        self, route_handler: HTTPRouteHandler, http_method: HttpMethod
    ) -> Operation:
        operation_id = self.create_operation_id(route_handler, http_method)
        parameter_factory = ParameterFactory(self.context, route_handler, self.route.path_parameters)
        parameters = parameter_factory.create_parameters_for_handler()
        signature_fields = route_handler.signature_model._fields

        request_body = None
        if data_field := signature_fields.get("data"):
            request_body = RequestBodyFactory(self.context).create_request_body(
                route_handler=route_handler, field_definition=data_field
            )

        raises_validation_error = bool("data" in signature_fields or self._path_item.parameters or parameters)
        responses = ResponseFactory(self.context, route_handler).create_responses(
            raises_validation_error=raises_validation_error,
        )

        return route_handler.operation_class(
            operation_id=operation_id,
            tags=route_handler.resolve_tags() or None,
            summary=route_handler.summary or SEPARATORS_CLEANUP_PATTERN.sub("", route_handler.handler_name.title()),
            description=self.get_description_for_handler(route_handler),
            deprecated=route_handler.deprecated,
            responses=responses,
            request_body=request_body,
            parameters=parameters or None,  # type: ignore[arg-type]
            security=route_handler.resolve_security() or None,
        )

    def create_operation_id(self, route_handler: HTTPRouteHandler, http_method: HttpMethod) -> str:
        if isinstance(route_handler.operation_id, str):
            operation_id = route_handler.operation_id
        elif callable(route_handler.operation_id):
            operation_id = route_handler.operation_id(route_handler, http_method, self.route.path_components)
        else:
            operation_id = self.context.openapi_config.operation_id_creator(
                route_handler, http_method, self.route.path_components
            )
        self.context.add_operation_id(operation_id)
        return operation_id

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
