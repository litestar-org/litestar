from typing import Any, Callable, Dict, List, Optional, Sequence, Union, cast
from urllib.parse import urlencode

from orjson import dumps
from pydantic import BaseModel
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.testclient import TestClient as StarletteTestClient
from typing_extensions import Type

from starlite import Controller, Provide, Router
from starlite.app import Starlite
from starlite.enums import HttpMethod
from starlite.handlers import RouteHandler
from starlite.openapi import OpenAPIConfig


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
        Union[Type[Controller], RouteHandler, Router, Callable],
        List[Union[Type[Controller], RouteHandler, Router, Callable]],
    ],
    dependencies: Optional[Dict[str, Provide]] = None,
    exception_handlers: Any = None,
    middleware: Sequence[Middleware] = None,
    on_shutdown: Optional[Sequence[Callable]] = None,
    on_startup: Optional[Sequence[Callable]] = None,
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
    content: Optional[Union[Dict[str, Any], BaseModel]] = None,
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
    if query:
        scope["query_string"] = urlencode(query, doseq=True)
    if headers:
        scope["headers"] = [
            (key.lower().encode("latin-1", errors="ignore"), value.encode("latin-1", errors="ignore"))
            for key, value in headers.items()
        ]
    request = Request(scope=scope)
    if content:
        if isinstance(content, BaseModel):
            request._body = content.json().encode("utf-8")
        else:
            request._body = dumps(content)
    return request
