from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Optional,
    Set,
    Tuple,
    Type,
    Union,
)
from urllib.parse import urlencode

from pydantic import AnyUrl, BaseConfig, BaseModel, DirectoryPath, constr, validator
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
from starlette.staticfiles import StaticFiles
from typing_extensions import Literal

from starlite.cache import CacheBackendProtocol, SimpleCacheBackend
from starlite.openapi.controller import OpenAPIController
from starlite.openapi.path_item import create_path_item
from starlite.routes import HTTPRoute
from starlite.template import TemplateEngineProtocol
from starlite.types import CacheKeyBuilder, Method
from starlite.utils import normalize_path

if TYPE_CHECKING:
    from starlette.types import ASGIApp

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
    """Enumerates available compression backends."""

    GZIP = "gzip"
    BROTLI = "brotli"


class BrotliMode(str, Enum):
    """Enumerates the available brotli compression optimization modes."""

    GENERIC = "generic"
    TEXT = "text"
    FONT = "font"


class CompressionConfig(BaseModel):
    """Class containing the configuration for request compression."""

    backend: Union[CompressionBackend, str]
    minimum_size: int = 500
    """Minimum response size (bytes) to enable compression, affects all backends."""
    gzip_compress_level: int = 9
    """Range [0-9], see [official docs](https://docs.python.org/3/library/gzip.html)."""
    brotli_quality: int = 5
    """
    Range [0-11], Controls the compression-speed vs compression-density tradeoff. The higher the quality, the slower
    the compression.
    """
    brotli_mode: Union[BrotliMode, str] = BrotliMode.TEXT
    """
    MODE_GENERIC, MODE_TEXT (for UTF-8 format text input, default) or MODE_FONT (for WOFF 2.0).
    """
    brotli_lgwin: int = 22
    """
    Base 2 logarithm of size. Range is 10 to 24. Defaults to 22.
    """
    brotli_lgblock: int = 0
    """
    Base 2 logarithm of the maximum input block size. Range is 16 to 24. If set to 0, the value will be set based on the
    quality. Defaults to 0.
    """
    brotli_gzip_fallback: bool = True
    """
    Use GZIP if Brotli not supported.
    """

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


class CSRFConfig(BaseModel):
    """CSRF middleware configuration."""

    secret: str
    """A string that is used to create an HMAC to sign the CSRF token"""
    cookie_name: str = "csrftoken"
    """The CSRF cookie name"""
    cookie_path: str = "/"
    """The CSRF cookie path"""
    header_name: str = "x-csrftoken"
    """The header that will be expected in each request"""
    cookie_secure: bool = False
    """A boolean value indicating whether to set the `Secure` attribute on the cookie"""
    cookie_httponly: bool = False
    """A boolean value indicating whether to set the `HttpOnly` attribute on the cookie"""
    cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    """The value to set in the `SameSite` attribute of the cookie"""
    cookie_domain: Optional[str] = None
    """Specifies which hosts can receive the cookie"""
    safe_methods: Set[Method] = {"GET", "HEAD"}
    """A set of "safe methods" that can set the cookie"""


class OpenAPIConfig(BaseModel):
    """
    OpenAPI Settings and Schema Properties.
    """

    class Config(BaseConfig):
        copy_on_model_validation = False

    create_examples: bool = False
    """Generate examples with `pydantic - factories`"""
    openapi_controller: Type[OpenAPIController] = OpenAPIController
    """Controller for generating OpenAPI routes. Must be subclass of [OpenAPIController][starlite.openapi.controller.OpenAPIController]"""

    title: str
    """Title of API documentation"""
    version: str
    """API version"""
    contact: Optional[Contact] = None
    """`pydantic_openapi_schema.v3_10_0.Contact`"""
    description: Optional[str] = None
    """API description text"""
    external_docs: Optional[ExternalDocumentation] = None
    """`pydantic_openapi_schema.v3_10_0.external_documentation.ExternalDocumentation`"""
    license: Optional[License] = None
    """`pydantic_openapi_schema.v3_10_0.license.License`"""
    security: Optional[List[SecurityRequirement]] = None
    """`pydantic_openapi_schema.v3_10_0.security_requirement.SecurityRequirement`"""
    servers: List[Server] = [Server(url="/")]
    """`pydantic_openapi_schema.v3_10_0.server.Server`"""
    summary: Optional[str] = None
    """Summary text"""
    tags: Optional[List[Tag]] = None
    """`pydantic_openapi_schema.v3_10_0.tag.Tag`"""
    terms_of_service: Optional[AnyUrl] = None
    """URL to page that contains terms of service"""
    use_handler_docstrings: bool = False
    """Draw operation description from route handler docstring if not otherwise provided."""
    webhooks: Optional[Dict[str, Union[PathItem, Reference]]] = None
    """
    `pydantic_openapi_schema.v3_10_0.path_item.PathItem`
    `pydantic_openapi_schema.v3_10_0.reference.Reference`
    """

    def to_openapi_schema(self) -> OpenAPI:
        """
        Generates an OpenAPI model

        Returns:
            pydantic_openapi_schema.v3_10_0.open_api.OpenAPI
        """
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
        Creates `OpenAPI` instance for the given `app`.

        Args:
            app (Starlite): [Starlite][starlite.app.Starlite] instance.

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

    @validator("path")
    def validate_path(cls, value: str) -> str:  # pylint: disable=no-self-argument
        """
        Ensures the the path has not path parameters

        Args:
            value: A path string

        Returns:
            The passed in value
        """
        if "{" in value:
            raise ValueError("path parameters are not supported for static files")
        return normalize_path(value)

    def to_static_files_app(self) -> "ASGIApp":
        """
                Returns an ASGI app serving static files based on the config

                Returns:
        ^           [StaticFiles][starlette.static_files.StaticFiles]
        """
        static_files = StaticFiles(
            html=self.html_mode,
            check_dir=False,
            directory=str(self.directories[0]),
        )
        static_files.all_directories = self.directories  # type: ignore[assignment]
        return static_files


class TemplateConfig(BaseModel):
    class Config(BaseConfig):
        arbitrary_types_allowed = True
        copy_on_model_validation = False

    directory: Union[DirectoryPath, List[DirectoryPath]]
    engine: Type[TemplateEngineProtocol]
    engine_callback: Optional[Callable[[Any], Any]]


def default_cache_key_builder(request: "Request") -> str:
    """
    Given a request object, returns a cache key by combining the path with the sorted query params

    Args:
        request (Request): request used to generate cache key.

    Returns:
        str: combination of url path and query parameters
    """
    qp: List[Tuple[str, Any]] = list(request.query_params.items())
    qp.sort(key=lambda x: x[0])
    return request.url.path + urlencode(qp, doseq=True)


class CacheConfig(BaseModel):
    class Config(BaseConfig):
        arbitrary_types_allowed = True
        copy_on_model_validation = False

    backend: CacheBackendProtocol = SimpleCacheBackend()
    """
    Instance conforming to [CacheBackendProtocol][starlite.cache.CacheBackendProtocol], default
    [SimpleCacheBackend()][starlite.cache.SimpleCacheBackend]
    """
    expiration: int = 60  # value in seconds
    """Default cache expiration in seconds"""
    cache_key_builder: CacheKeyBuilder = default_cache_key_builder
    """
    [CacheKeyBuilder][starlite.types.CacheKeyBuilder],
    [default_cache_key_builder][starlite.config.default_cache_key_builder] if not provided
    """
