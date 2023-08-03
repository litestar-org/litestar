from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.enums import RequestEncodingType
from litestar.openapi.spec.media_type import OpenAPIMediaType
from litestar.openapi.spec.request_body import RequestBody
from litestar.params import BodyKwarg

__all__ = ("create_request_body",)


if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar.handlers import BaseRouteHandler
    from litestar.typing import FieldDefinition


def create_request_body(
    route_handler: BaseRouteHandler, field_definition: FieldDefinition, schema_creator: SchemaCreator
) -> RequestBody | None:
    """Create a RequestBody model for the given RouteHandler or return None."""
    media_type: RequestEncodingType | str = RequestEncodingType.JSON
    if isinstance(field_definition.kwarg_definition, BodyKwarg) and field_definition.kwarg_definition.media_type:
        media_type = field_definition.kwarg_definition.media_type

    if dto := route_handler.resolve_data_dto():
        schema = dto.create_openapi_schema(
            field_definition=field_definition, handler_id=route_handler.handler_id, schema_creator=schema_creator
        )
    else:
        schema = schema_creator.for_field_definition(field_definition)

    return RequestBody(required=True, content={media_type: OpenAPIMediaType(schema=schema)})
