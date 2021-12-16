from typing import Any, Callable, Dict, List, Optional, Sequence, Union, cast
from urllib.parse import urlencode

from openapi_schema_pydantic import (
    Contact,
    ExternalDocumentation,
    License,
    PathItem,
    Reference,
    SecurityRequirement,
    Server,
    Tag,
)
from orjson import dumps
from pydantic import AnyUrl, BaseModel
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.testclient import TestClient
from typing_extensions import AsyncContextManager, Type

from starlite import Controller, Provide, Router
from starlite.app import Starlite
from starlite.enums import HttpMethod, OpenAPIMediaType
from starlite.handlers import RouteHandler


def create_test_client(
    route_handlers: Union[
        Union[Type[Controller], RouteHandler, Router, Callable],
        List[Union[Type[Controller], RouteHandler, Router, Callable]],
    ],
    dependencies: Optional[Dict[str, Provide]] = None,
    exception_handlers: Any = None,
    lifespan: Optional[Callable[[Any], AsyncContextManager]] = None,
    middleware: Sequence[Middleware] = None,
    on_shutdown: Optional[Sequence[Callable]] = None,
    on_startup: Optional[Sequence[Callable]] = None,
    base_url: str = "http://testserver",
    raise_server_exceptions: bool = True,
    root_path: str = "",
    backend: str = "asyncio",
    backend_options: Optional[Dict[str, Any]] = None,
    # openapi config below
    openapi_schema_url: str = "/schema",
    openapi_media_type: OpenAPIMediaType = OpenAPIMediaType.OPENAPI_YAML,
    title: str = "StarLite API",
    version: str = "1.0.0",
    contact: Optional[Contact] = None,
    description: Optional[str] = None,
    external_docs: Optional[ExternalDocumentation] = None,
    license: Optional[License] = None,  # pylint: disable=redefined-builtin
    security: Optional[List[SecurityRequirement]] = None,
    servers: Optional[List[Server]] = None,
    summary: Optional[str] = None,
    tags: Optional[List[Tag]] = None,
    terms_of_service: Optional[AnyUrl] = None,
    webhooks: Optional[Dict[str, Union[PathItem, Reference]]] = None,
) -> TestClient:
    """Create a TestClient"""
    app = Starlite(
        dependencies=dependencies,
        exception_handlers=exception_handlers,
        lifespan=lifespan,
        middleware=middleware,
        on_shutdown=on_shutdown,
        on_startup=on_startup,
        route_handlers=cast(Any, route_handlers if isinstance(route_handlers, list) else [route_handlers]),
        openapi_schema_url=openapi_schema_url,
        openapi_media_type=openapi_media_type,
        title=title,
        version=version,
        contact=contact,
        description=description,
        external_docs=external_docs,
        license=license,
        security=security,
        servers=servers,
        summary=summary,
        tags=tags,
        terms_of_service=terms_of_service,
        webhooks=webhooks,
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
