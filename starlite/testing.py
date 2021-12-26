from typing import Any, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import urlencode

from orjson import dumps
from pydantic import BaseModel
from pydantic.typing import AnyCallable, NoArgAnyCallable
from requests.models import RequestEncodingMixin
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.testclient import TestClient as StarletteTestClient
from typing_extensions import Type

from starlite import Controller, Provide, Router
from starlite.app import Starlite
from starlite.enums import HttpMethod, RequestEncodingType
from starlite.handlers import RouteHandler
from starlite.openapi.config import OpenAPIConfig
from starlite.types import EXCEPTION_HANDLER, MiddlewareProtocol


class RequestEncoder(RequestEncodingMixin):
    def multipart_encode(self, data: Dict[str, Any]) -> Tuple[bytes, str]:
        class ForceMultipartDict(dict):  # type: ignore
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
        Union[Type[Controller], RouteHandler, Router, AnyCallable],
        List[Union[Type[Controller], RouteHandler, Router, AnyCallable]],
    ],
    dependencies: Optional[Dict[str, Provide]] = None,
    exception_handlers: Optional[Dict[Union[int, Type[Exception]], EXCEPTION_HANDLER]] = None,
    middleware: Optional[List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]]] = None,
    on_shutdown: Optional[List[NoArgAnyCallable]] = None,
    on_startup: Optional[List[NoArgAnyCallable]] = None,
    base_url: str = "http://testserver",
    raise_server_exceptions: bool = True,
    root_path: str = "",
    backend: str = "asyncio",
    backend_options: Optional[Dict[str, Any]] = None,
    openapi_config: Optional[OpenAPIConfig] = None,
) -> TestClient:
    """Create a TestClient"""
    app = Starlite(
        dependencies=dependencies,
        exception_handlers=exception_handlers,
        middleware=middleware,
        on_shutdown=on_shutdown,
        on_startup=on_startup,
        route_handlers=cast(Any, route_handlers if isinstance(route_handlers, list) else [route_handlers]),
        openapi_config=openapi_config,
    )
    return TestClient(
        app=app,
        base_url=base_url,
        raise_server_exceptions=raise_server_exceptions,
        root_path=root_path,
        backend=backend,
        backend_options=backend_options,
    )


def create_test_request(
    http_method: HttpMethod = HttpMethod.GET,
    scheme: str = "http",
    server: str = "test.org",
    port: int = 3000,
    root_path: str = "/",
    path: str = "",
    query: Optional[Dict[str, Union[str, List[str]]]] = None,
    headers: Optional[Dict[str, str]] = None,
    cookie: Optional[str] = None,
    content: Optional[Union[Dict[str, Any], BaseModel]] = None,
    request_media_type: RequestEncodingType = RequestEncodingType.JSON,
) -> Request:
    """Create a starlette request using passed in parameters"""
    scope = dict(
        type="http",
        method=http_method,
        scheme=scheme,
        server=(server, port),
        root_path=root_path,
        path=path,
        headers=[],
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
    request = Request(scope=scope)
    if body:
        request._body = body
    return request
