from typing import TYPE_CHECKING, List, Optional, Union

from pydantic_openapi_schema.v3_1_0.media_type import (
    MediaType as OpenAPISchemaMediaType,
)
from pydantic_openapi_schema.v3_1_0.request_body import RequestBody

from starlite._openapi.schema import create_schema, update_schema_with_signature_field
from starlite.enums import RequestEncodingType
from starlite.params import BodyKwarg

__all__ = ("create_request_body",)


if TYPE_CHECKING:
    from starlite._signature.models import SignatureField
    from starlite.plugins.base import OpenAPISchemaPluginProtocol


def create_request_body(
    field: "SignatureField", generate_examples: bool, plugins: List["OpenAPISchemaPluginProtocol"]
) -> Optional[RequestBody]:
    """Create a RequestBody model for the given RouteHandler or return None."""
    media_type: Union[RequestEncodingType, str] = RequestEncodingType.JSON
    if isinstance(field.kwarg_model, BodyKwarg) and field.kwarg_model.media_type:
        media_type = field.kwarg_model.media_type

    schema = create_schema(field=field, generate_examples=generate_examples, plugins=plugins)
    update_schema_with_signature_field(schema=schema, signature_field=field)
    return RequestBody(required=True, content={media_type: OpenAPISchemaMediaType(media_type_schema=schema)})
