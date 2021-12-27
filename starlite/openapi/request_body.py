from typing import Optional

from openapi_schema_pydantic import MediaType as OpenAPISchemaMediaType
from openapi_schema_pydantic import RequestBody
from pydantic.fields import ModelField

from starlite.enums import RequestEncodingType
from starlite.openapi.schema import create_schema, update_schema_with_field_info


def create_request_body(field: ModelField, generate_examples: bool) -> Optional[RequestBody]:
    """
    Create a RequestBody model for the given RouteHandler or return None
    """
    media_type = field.field_info.extra.get("media_type", RequestEncodingType.JSON)
    schema = create_schema(field=field, generate_examples=generate_examples)
    update_schema_with_field_info(schema=schema, field_info=field.field_info)
    return RequestBody(content={media_type: OpenAPISchemaMediaType(media_type_schema=schema)})
