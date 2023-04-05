from __future__ import annotations

from typing import TYPE_CHECKING

from starlite._openapi.schema_generation import create_schema
from starlite.enums import RequestEncodingType
from starlite.openapi.spec.media_type import OpenAPIMediaType
from starlite.openapi.spec.request_body import RequestBody
from starlite.params import BodyKwarg

__all__ = ("create_request_body",)


if TYPE_CHECKING:
    from starlite._signature.field import SignatureField
    from starlite.openapi.spec import Schema
    from starlite.plugins import OpenAPISchemaPluginProtocol


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
