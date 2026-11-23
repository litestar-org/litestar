from __future__ import annotations

from typing import TYPE_CHECKING, Any

from litestar._openapi.schema_generation import SchemaCreator
from litestar.dto._plan import create_dto_openapi_schema
from litestar.enums import RequestEncodingType
from litestar.openapi.spec.media_type import OpenAPIMediaType
from litestar.openapi.spec.request_body import RequestBody
from litestar.params import BodyKwarg

__all__ = ("create_request_body",)


if TYPE_CHECKING:
    from litestar._openapi.datastructures import OpenAPIContext
    from litestar.handlers.base import BaseRouteHandler
    from litestar.typing import FieldDefinition


def create_request_body(
    context: OpenAPIContext,
    route_handler: BaseRouteHandler,
    data_field: FieldDefinition,
    signature_namespace: dict[str, Any] | None = None,
) -> RequestBody:
    """Create a RequestBody instance for the given route handler's data field.

    Args:
        context: The OpenAPIContext instance.
        route_handler: The route handler.
        data_field: The data field.
        signature_namespace: Additional names for forward reference resolution.

    Returns:
        A RequestBody instance.
    """
    media_type: RequestEncodingType | str = RequestEncodingType.JSON
    schema_creator = SchemaCreator.from_openapi_context(
        context, prefer_alias=True, signature_namespace=signature_namespace
    )
    if isinstance(data_field.kwarg_definition, BodyKwarg) and data_field.kwarg_definition.media_type:
        media_type = data_field.kwarg_definition.media_type

    if (plan := route_handler._dto_plan) is not None and plan.data is not None:
        schema = create_dto_openapi_schema(plan.data, data_field, route_handler, schema_creator)
    else:
        schema = schema_creator.for_field_definition(data_field)

    return RequestBody(required=not data_field.is_optional, content={media_type: OpenAPIMediaType(schema=schema)})
