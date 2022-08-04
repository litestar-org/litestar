from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
)
from urllib.parse import urlencode

from pydantic import AnyUrl, BaseModel, DirectoryPath, constr, validator
from pydantic_openapi_schema.utils import construct_open_api_with_schema_class
from pydantic_openapi_schema.v3_1_0.contact import Contact
from pydantic_openapi_schema.v3_1_0.external_documentation import ExternalDocumentation
from pydantic_openapi_schema.v3_1_0.info import Info
from pydantic_openapi_schema.v3_1_0.license import License
from pydantic_openapi_schema.v3_1_0.open_api import OpenAPI
from pydantic_openapi_schema.v3_1_0.path_item import PathItem
from pydantic_openapi_schema.v3_1_0.reference import Reference
from pydantic_openapi_schema.v3_1_0.security_requirement import SecurityRequirement
from pydantic_openapi_schema.v3_1_0.server import Server
from pydantic_openapi_schema.v3_1_0.tag import Tag

from starlite.cache import CacheBackendProtocol, SimpleCacheBackend
from starlite.openapi.controller import OpenAPIController
from starlite.openapi.path_item import create_path_item
from starlite.routes import HTTPRoute
from starlite.template import TemplateEngineProtocol
from starlite.types import CacheKeyBuilder

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.connection import Request


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

    backend: Union[CompressionBackend, str]
    minimum_size: int = 500
    gzip_compress_level: int = 9
    brotli_quality: int = 5
    brotli_mode: Union[BrotliMode, str] = BrotliMode.TEXT
    brotli_lgwin: int = 22
    brotli_lgblock: int = 0
    brotli_gzip_fallback: bool = True

    @validator("backend", pre=True, always=True)
    def backend_must_be_supported(  # pylint: disable=no-self-argument
        cls, v: Union[CompressionBackend, str]
    ) -> CompressionBackend:
        """Compression Backend Validation

        Args:
            v (CompressionBackend|str): Holds the selected compression backend

        Raises:
            ValueError: Value is not a valid compression backend

        Returns:
            _type_: CompressionBackend
        """
        if isinstance(v, str):
            try:
                v = CompressionBackend[v.upper()]
            except KeyError as e:
                raise ValueError(f"{v} is not a valid compression backend") from e
        return v

    @validator("brotli_mode", pre=True, always=True)
    def brotli_mode_must_be_valid(cls, v: Union[BrotliMode, str]) -> BrotliMode:  # pylint: disable=no-self-argument
        """Compression Backend Validation

        Args:
            v (CompressionBackend|str): Holds the selected compression backend

        Raises:
            ValueError: Value is not a valid compression backend

        Returns:
            _type_: CompressionBackend
        """
        if isinstance(v, str):
            try:
                v = BrotliMode[v.upper()]
            except KeyError as e:
                raise ValueError(f"{v} is not a valid compression optimization mode") from e
        return v

    def dict(self, *args, **kwargs) -> Dict[str, Any]:  # type: ignore[no-untyped-def]
        """Returns a dictionary representation of the CompressionConfig.

        Returns:
            Dict[str, Any]: dictionary representation of the selected CompressionConfig.  Only columns for the selected backend are included
        """
        brotli_keys = {
            "minimum_size",
            "brotli_quality",
            "brotli_mode",
            "brotli_lgwin",
            "brotli_lgblock",
            "brotli_gzip_fallback",
        }
        gzip_keys = {"minimum_size", "gzip_compress_level"}
        if self.backend == CompressionBackend.GZIP:
            kwargs["include"] = gzip_keys
        elif self.backend == CompressionBackend.BROTLI:
            kwargs["include"] = brotli_keys
        else:
            kwargs["include"] = brotli_keys.union(gzip_keys)

        return super().dict(*args, **kwargs)


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
    use_handler_docstrings: bool = False
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

    def create_openapi_schema_model(self, app: "Starlite") -> OpenAPI:
        """
        Creates `OpenAPI` instance for the given `router`.

        Args:
            app (Starlite)

        Returns:
            OpenAPI
        """
        schema = self.to_openapi_schema()
        schema.paths = {}
        for route in app.routes:
            if (
                isinstance(route, HTTPRoute)
                and any(route_handler.include_in_schema for route_handler, _ in route.route_handler_map.values())
                and (route.path_format or "/") not in schema.paths
            ):
                schema.paths[route.path_format or "/"] = create_path_item(
                    route=route,
                    create_examples=self.create_examples,
                    plugins=app.plugins,
                    use_handler_docstrings=self.use_handler_docstrings,
                )
        return construct_open_api_with_schema_class(schema)


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


def default_cache_key_builder(request: "Request") -> str:
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
