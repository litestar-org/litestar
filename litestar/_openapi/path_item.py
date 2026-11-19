from __future__ import annotations

import dataclasses
from typing import TYPE_CHECKING

from litestar._openapi.operation import describe_operation
from litestar._openapi.parameters import ParameterFactory
from litestar._openapi.request_body import create_request_body
from litestar._openapi.responses import ResponseFactory
from litestar._openapi.utils import supports_openapi_3_2
from litestar.enums import HttpMethod
from litestar.exceptions import ImproperlyConfiguredException
from litestar.openapi.spec import PathItem

if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar._openapi.operation import OperationDescription
    from litestar.openapi.spec import Operation
    from litestar.routes import HTTPRoute

__all__ = ("PathItemFactory", "create_operation", "merge_path_item_operations")

OPERATION_FIELDS = ("get", "put", "post", "delete", "options", "head", "patch", "trace", "query")


class PathItemFactory:
    """Factory for creating a PathItem instance for a given route."""

    def __init__(self, openapi_context: OpenAPIContext, route: HTTPRoute) -> None:
        self.context = openapi_context
        self.route = route
        self._path_item = PathItem()

    def create_path_item(self) -> PathItem:
        """Create a PathItem for the given route parsing all http_methods into Operation Models.

        Returns:
            A PathItem instance.
        """
        for http_method, route_handler in self.route.route_handler_map.items():
            if not route_handler.include_in_schema:
                continue

            if http_method == HttpMethod.QUERY and not supports_openapi_3_2(
                self.context.openapi_config.openapi_version
            ):
                continue

            operation = describe_operation(
                route_handler,
                HttpMethod(http_method),
                openapi_config=self.context.openapi_config,
                path_components=self.route.path_components,
                path_parameters=self.route.path_parameters,
            )
            setattr(self._path_item, http_method.lower(), create_operation(self.context, operation))

        return self._path_item


def create_operation(context: OpenAPIContext, operation: OperationDescription) -> Operation:
    """Create an Operation from its description.

    Adds the operation id to the context's operation id set, where it is checked for uniqueness.

    Args:
        context: The OpenAPIContext instance.
        operation: The description of the operation.

    Returns:
        An Operation instance.
    """
    context.add_operation_id(operation.operation_id)
    parameters = ParameterFactory(context, operation).create_parameters()

    request_body = None
    if operation.request_body is not None:
        request_body = create_request_body(
            context,
            operation.handler_id,
            operation.request_body.dto,
            operation.request_body.field_definition,
            signature_namespace=operation.signature_namespace,
        )

    return operation.operation_class(
        operation_id=operation.operation_id,
        tags=list(operation.tags) or None,
        summary=operation.summary,
        description=operation.description,
        deprecated=operation.deprecated,
        responses=ResponseFactory(context, operation).create_responses(),
        request_body=request_body,
        parameters=parameters or None,  # type: ignore[arg-type]
        security=None if operation.security is None else list(operation.security),
    )


def merge_path_item_operations(source: PathItem, other: PathItem, for_path: str) -> PathItem:
    """Merge operations from path items, creating a new path item that includes
    operations from both.
    """
    fields = {f.name for f in dataclasses.fields(PathItem)}.difference(OPERATION_FIELDS)
    if any(getattr(source, attr) and getattr(other, attr) for attr in OPERATION_FIELDS):
        raise ValueError("Cannot merge operation for PathItem if operation is set on both items")

    if differing_values := [
        (value_a, value_b) for attr in fields if (value_a := getattr(source, attr)) != (value_b := getattr(other, attr))
    ]:
        raise ImproperlyConfiguredException(
            f"Conflicting OpenAPI path configuration for {for_path!r}. "
            f"{', '.join(f'{a} != {b}' for a, b in differing_values)}"
        )

    return dataclasses.replace(
        source, **{attr: getattr(source, attr) or getattr(other, attr) for attr in OPERATION_FIELDS}
    )
