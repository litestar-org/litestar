from __future__ import annotations

from typing import TYPE_CHECKING

from litestar.enums import RequestEncodingType
from litestar.openapi.spec.media_type import OpenAPIMediaType
from litestar.openapi.spec.request_body import RequestBody
from litestar.params import BodyKwarg

__all__ = ("create_request_body",)


if TYPE_CHECKING:
    from litestar._openapi.schema_generation import SchemaCreator
    from litestar._signature.field import SignatureField
    from litestar.handlers import BaseRouteHandler


def create_request_body(
    route_handler: BaseRouteHandler, field: SignatureField, schema_creator: SchemaCreator
) -> RequestBody | None:
    """Create a RequestBody model for the given RouteHandler or return None."""
    media_type: RequestEncodingType | str = RequestEncodingType.JSON
    if isinstance(field.kwarg_model, BodyKwarg) and field.kwarg_model.media_type:
        media_type = field.kwarg_model.media_type

    if dto := route_handler.resolve_dto():
        schema = dto.create_openapi_schema("data", str(route_handler), schema_creator)
    else:
        schema = schema_creator.for_field(field)

    return RequestBody(required=True, content={media_type: OpenAPIMediaType(schema=schema)})
