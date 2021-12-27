from typing import Dict, List, Optional, Union

from openapi_schema_pydantic import (
    Contact,
    ExternalDocumentation,
    Info,
    License,
    OpenAPI,
    PathItem,
    Reference,
    SecurityRequirement,
    Server,
    Tag,
)
from pydantic import AnyUrl, BaseModel

from starlite.enums import OpenAPIMediaType


class CORSConfig(BaseModel):
    allow_origins: List[str] = ["*"]
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]
    allow_credentials: bool = False
    allow_origin_regex: Optional[str] = None
    expose_headers: List[str] = []
    max_age: int = 600


class SchemaGenerationConfig(BaseModel):
    """Class containing generator settings"""

    # endpoint config
    schema_endpoint_url: str = "/schema"
    schema_response_media_type: OpenAPIMediaType = OpenAPIMediaType.OPENAPI_YAML
    # determines whether examples will be auto-generated using the pydantic-factories library
    create_examples: bool = False


class OpenAPIConfig(SchemaGenerationConfig):
    """Class containing Settings and Schema Properties"""

    title: str = "StarLite API"
    version: str = "1.0.0"
    contact: Optional[Contact] = None
    description: Optional[str] = None
    external_docs: Optional[ExternalDocumentation] = None
    license: Optional[License] = None
    security: Optional[List[SecurityRequirement]] = None
    servers: List[Server] = [Server(url="/")]
    summary: Optional[str] = None
    tags: Optional[List[Tag]] = None
    terms_of_service: Optional[AnyUrl] = None
    webhooks: Optional[Dict[str, Union[PathItem, Reference]]] = None

    def to_openapi_schema(self) -> OpenAPI:
        """Generates an OpenAPI model"""
        return OpenAPI(
            externalDocs=self.external_docs,
            security=self.security,
            servers=self.servers,
            tags=self.tags,
            webhooks=self.webhooks,
            info=Info(
                title=self.title,
                version=self.version,
                description=self.description,
                contact=self.contact,
                license=self.license,
                summary=self.summary,
                termsOfService=self.terms_of_service,
            ),
        )

    def to_schema_generation_config(self) -> SchemaGenerationConfig:
        """Create a SchemaGenerationConfig"""
        return SchemaGenerationConfig(
            schema_endpoint_url=self.schema_endpoint_url,
            schema_response_media_type=self.schema_response_media_type,
            create_examples=self.create_examples,
        )
