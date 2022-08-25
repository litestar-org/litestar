from typing import TYPE_CHECKING, List, Optional

from pydantic_openapi_schema.v3_1_0.media_type import (
    MediaType as OpenAPISchemaMediaType,
)
from pydantic_openapi_schema.v3_1_0.request_body import RequestBody

from starlite.enums import RequestEncodingType
from starlite.openapi.schema import create_schema, update_schema_with_field_info

if TYPE_CHECKING:
    from pydantic.fields import ModelField

    from starlite.plugins.base import PluginProtocol


def create_request_body(
    field: "ModelField", generate_examples: bool, plugins: List["PluginProtocol"]
) -> Optional[RequestBody]:
    """Create a RequestBody model for the given RouteHandler or return None."""
    media_type = field.field_info.extra.get("media_type", RequestEncodingType.JSON)
    schema = create_schema(field=field, generate_examples=generate_examples, plugins=plugins)
    update_schema_with_field_info(schema=schema, field_info=field.field_info)
    return RequestBody(required=True, content={media_type: OpenAPISchemaMediaType(media_type_schema=schema)})
