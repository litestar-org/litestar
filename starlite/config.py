from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

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
from pydantic import AnyUrl, BaseModel, DirectoryPath, constr
from typing_extensions import Type

from starlite.cache import CacheBackendProtocol, SimpleCacheBackend
from starlite.connection import Request
from starlite.openapi.controller import OpenAPIController
from starlite.template import TemplateEngineProtocol
from starlite.types import CacheKeyBuilder


class CORSConfig(BaseModel):
    allow_origins: List[str] = ["*"]
    allow_methods: List[str] = ["*"]
    allow_headers: List[str] = ["*"]
    allow_credentials: bool = False
    allow_origin_regex: Optional[str] = None
    expose_headers: List[str] = []
    max_age: int = 600


class OpenAPIConfig(BaseModel):
    """Class containing Settings and Schema Properties"""

    create_examples: bool = False
    openapi_controller: Type[OpenAPIController] = OpenAPIController

    title: str
    version: str
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


class StaticFilesConfig(BaseModel):
    path: constr(min_length=1)  # type: ignore
    directories: List[DirectoryPath]
    html_mode: bool = False


class TemplateConfig(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    directory: Union[DirectoryPath, List[DirectoryPath]]
    engine: Type[TemplateEngineProtocol]


def default_cache_key_builder(request: Request) -> str:
    """
    Given a request object, returns a cache key by combining the path with the sorted query params
    """
    qp: List[Tuple[str, Any]] = list(request.query_params.items())
    qp.sort(key=lambda x: x[0])
    return request.url.path + urlencode(qp, doseq=True)


class CacheConfig(BaseModel):
    class Config:
        arbitrary_types_allowed = True

    backend: CacheBackendProtocol = SimpleCacheBackend()
    expiration: int = 60  # value in seconds
    cache_key_builder: CacheKeyBuilder = default_cache_key_builder
