from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from urllib.parse import urlencode

from openapi_schema_pydantic.v3.v3_1_0.contact import Contact
from openapi_schema_pydantic.v3.v3_1_0.external_documentation import (
    ExternalDocumentation,
)
from openapi_schema_pydantic.v3.v3_1_0.info import Info
from openapi_schema_pydantic.v3.v3_1_0.license import License
from openapi_schema_pydantic.v3.v3_1_0.open_api import OpenAPI
from openapi_schema_pydantic.v3.v3_1_0.path_item import PathItem
from openapi_schema_pydantic.v3.v3_1_0.reference import Reference
from openapi_schema_pydantic.v3.v3_1_0.security_requirement import SecurityRequirement
from openapi_schema_pydantic.v3.v3_1_0.server import Server
from openapi_schema_pydantic.v3.v3_1_0.tag import Tag
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


class CompressionBackend(str, Enum):
    """CompressionBackend is an enum that defines the available compression backends."""

    GZIP = "gzip"
    BROTLI = "brotli"


class BrotliMode(str, Enum):
    """BrotliMode is an enum that defines the available brotli compression optimization modes."""

    GENERIC = "generic"
    TEXT = "text"
    FONT = "font"


class CompressionConfig(BaseModel):
    """Class containing the configuration for request compression."""

    backend: CompressionBackend
    minimum_size: int = 500
    gzip_compress_level: int = 9
    brotli_quality: int = 5
    brotli_mode: BrotliMode = BrotliMode.TEXT
    brotli_lgwin: int = 22
    brotli_lgblock: int = 0
    brotli_gzip_fallback: bool = True

    def dict(self) -> Dict[str, Any]:
        """Returns a dictionary representation of the CompressionConfig.

        Returns:
            Dict[str, Any]: dictionary representation of the selected CompressionConfig.  Only columns for the selected backend are included
        """
        default_keys = set({"backend"})
        brotli_keys = set({"brotli_quality", "brotli_mode", "brotli_lgwin", "brotli_lgblock", "brotli_gzip_fallback"})
        gzip_keys = set({"gzip_compress_level"})
        if self.backend == CompressionBackend.GZIP:
            excluded_keys = default_keys.union(brotli_keys)
        elif self.backend == CompressionBackend.BROTLI:
            excluded_keys = default_keys.union(gzip_keys)
        else:
            excluded_keys = default_keys.union(brotli_keys).union(gzip_keys)
        return super().dict(exclude=excluded_keys)


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
    engine_callback: Optional[Callable[[Any], Any]]


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
