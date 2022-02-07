from typing import Any, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import urlencode

from orjson import dumps
from pydantic import BaseModel
from pydantic.typing import AnyCallable
from requests.models import RequestEncodingMixin
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.testclient import TestClient as StarletteTestClient
from typing_extensions import Type

from starlite.app import DEFAULT_CACHE_CONFIG, Starlite
from starlite.config import (
    CacheConfig,
    CORSConfig,
    OpenAPIConfig,
    StaticFilesConfig,
    TemplateConfig,
)
from starlite.connection import Request
from starlite.controller import Controller
from starlite.datastructures import State
from starlite.enums import HttpMethod, RequestEncodingType
from starlite.handlers import BaseRouteHandler
from starlite.plugins.base import PluginProtocol
from starlite.provide import Provide
from starlite.router import Router
from starlite.types import (
    AfterRequestHandler,
    BeforeRequestHandler,
    ExceptionHandler,
    Guard,
    LifeCycleHandler,
    MiddlewareProtocol,
)


class RequestEncoder(RequestEncodingMixin):
    def multipart_encode(self, data: Dict[str, Any]) -> Tuple[bytes, str]:
        class ForceMultipartDict(dict):
            # code borrowed from here:
            # https://github.com/encode/starlette/blob/d222b87cb4601ecda5d642ab504a14974d364db4/tests/test_formparsers.py#L14
            def __bool__(self) -> bool:
                return True

        return self._encode_files(ForceMultipartDict(), data)  # type: ignore

    def url_encode(self, data: Dict[str, Any]) -> bytes:
        return self._encode_params(data).encode("utf-8")  # type: ignore


class TestClient(StarletteTestClient):
    app: Starlite

    def __init__(
        self,
        app: Starlite,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: str = "asyncio",
        backend_options: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(
            app=app,
            base_url=base_url,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
            backend=backend,
            backend_options=backend_options,
        )


def create_test_client(
    route_handlers: Union[
        Union[Type[Controller], BaseRouteHandler, Router, AnyCallable],
        List[Union[Type[Controller], BaseRouteHandler, Router, AnyCallable]],
    ],
    after_request: Optional[AfterRequestHandler] = None,
    allowed_hosts: Optional[List[str]] = None,
    backend: str = "asyncio",
    backend_options: Optional[Dict[str, Any]] = None,
    base_url: str = "http://testserver",
    before_request: Optional[BeforeRequestHandler] = None,
    cors_config: Optional[CORSConfig] = None,
    dependencies: Optional[Dict[str, Provide]] = None,
    exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
    guards: Optional[List[Guard]] = None,
    middleware: Optional[List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]]] = None,
    on_shutdown: Optional[List[LifeCycleHandler]] = None,
    on_startup: Optional[List[LifeCycleHandler]] = None,
    openapi_config: Optional[OpenAPIConfig] = None,
    template_config: Optional[TemplateConfig] = None,
    plugins: Optional[List[PluginProtocol]] = None,
    raise_server_exceptions: bool = True,
    root_path: str = "",
    static_files_config: Optional[Union[StaticFilesConfig, List[StaticFilesConfig]]] = None,
    cache_config: CacheConfig = DEFAULT_CACHE_CONFIG,
) -> TestClient:
    """Create a TestClient"""
    return TestClient(
        app=Starlite(
            after_request=after_request,
            allowed_hosts=allowed_hosts,
            before_request=before_request,
            cors_config=cors_config,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            middleware=middleware,
            on_shutdown=on_shutdown,
            on_startup=on_startup,
            openapi_config=openapi_config,
            template_config=template_config,
            plugins=plugins,
            route_handlers=cast(Any, route_handlers if isinstance(route_handlers, list) else [route_handlers]),
            static_files_config=static_files_config,
            cache_config=cache_config,
        ),
        backend=backend,
        backend_options=backend_options,
        base_url=base_url,
        raise_server_exceptions=raise_server_exceptions,
        root_path=root_path,
    )


def create_test_request(
    http_method: HttpMethod = HttpMethod.GET,
    app: Optional[Starlite] = None,
    content: Optional[Union[Dict[str, Any], BaseModel]] = None,
    cookie: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    path: str = "",
    port: int = 3000,
    query: Optional[Dict[str, Union[str, List[str]]]] = None,
    request_media_type: RequestEncodingType = RequestEncodingType.JSON,
    root_path: str = "/",
    scheme: str = "http",
    server: str = "test.org",
) -> Request:
    """Create a starlette request using passed in parameters"""

    class App:
        state = State()
        plugins: List[Any] = []

    scope = dict(
        type="http",
        method=http_method,
        scheme=scheme,
        server=(server, port),
        root_path=root_path,
        path=path,
        headers=[],
        app=app or App(),
    )
    if not headers:
        headers = {}
    if query:
        scope["query_string"] = urlencode(query, doseq=True)
    if cookie:
        headers["cookie"] = cookie
    body = None
    if content:
        if isinstance(content, BaseModel):
            content = content.dict()
        if request_media_type == RequestEncodingType.JSON:
            body = dumps(content)
            headers["Content-Type"] = RequestEncodingType.JSON.value
        elif request_media_type == RequestEncodingType.MULTI_PART:
            body, content_type = RequestEncoder().multipart_encode(content)
            headers["Content-Type"] = content_type
        else:
            body = RequestEncoder().url_encode(content)
            headers["Content-Type"] = RequestEncodingType.URL_ENCODED.value
    if headers:
        scope["headers"] = [
            (key.lower().encode("latin-1", errors="ignore"), value.encode("latin-1", errors="ignore"))
            for key, value in headers.items()
        ]
    request: Request[Any, Any] = Request(scope=scope)
    if body:
        request._body = body
    return request
