from __future__ import annotations

from typing import TYPE_CHECKING

from litestar._openapi.schema_generation import create_schema
from litestar.enums import RequestEncodingType
from litestar.openapi.spec.media_type import OpenAPIMediaType
from litestar.openapi.spec.request_body import RequestBody
from litestar.params import BodyKwarg

__all__ = ("create_request_body", "create_request_body_for_dto")


if TYPE_CHECKING:
    from litestar._signature.field import SignatureField
    from litestar.dto.interface import DTOInterface
    from litestar.handlers import BaseRouteHandler
    from litestar.openapi.spec import Schema
    from litestar.plugins import OpenAPISchemaPluginProtocol


def create_request_body(
    field: "SignatureField",
    generate_examples: bool,
    plugins: list["OpenAPISchemaPluginProtocol"],
    schemas: dict[str, "Schema"],
) -> RequestBody | None:
    """Create a RequestBody model for the given RouteHandler or return None."""
    media_type: RequestEncodingType | str = RequestEncodingType.JSON
    if isinstance(field.kwarg_model, BodyKwarg) and field.kwarg_model.media_type:
        media_type = field.kwarg_model.media_type

    schema = create_schema(field=field, generate_examples=generate_examples, plugins=plugins, schemas=schemas)
    return RequestBody(required=True, content={media_type: OpenAPIMediaType(schema=schema)})


def create_request_body_for_dto(
    handler: BaseRouteHandler,
    dto: type[DTOInterface],
    field: SignatureField,
    generate_examples: bool,
    schemas: dict[str, Schema],
) -> RequestBody | None:
    """Create a RequestBody model for the given RouteHandler or return None."""
    media_type: RequestEncodingType | str = RequestEncodingType.JSON
    if isinstance(field.kwarg_model, BodyKwarg) and field.kwarg_model.media_type:
        media_type = field.kwarg_model.media_type

    return dto.create_openapi_request_body(handler, generate_examples, media_type, schemas)
