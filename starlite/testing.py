from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, TypeVar, Union, cast
from urllib.parse import urlencode

from orjson import dumps
from pydantic import BaseModel
from starlette.testclient import TestClient as StarletteTestClient

from starlite import MissingDependencyException
from starlite.app import DEFAULT_CACHE_CONFIG, Starlite
from starlite.connection import Request
from starlite.datastructures import State
from starlite.enums import HttpMethod, ParamType, RequestEncodingType

if TYPE_CHECKING:
    from typing import Type

    from pydantic.fields import FieldInfo
    from pydantic.typing import AnyCallable

    from starlite.config import (
        CacheConfig,
        CompressionConfig,
        CORSConfig,
        OpenAPIConfig,
        StaticFilesConfig,
        TemplateConfig,
    )
    from starlite.controller import Controller
    from starlite.handlers import BaseRouteHandler
    from starlite.plugins.base import PluginProtocol
    from starlite.provide import Provide
    from starlite.router import Router
    from starlite.types import (
        AfterRequestHandler,
        AfterResponseHandler,
        BeforeRequestHandler,
        ExceptionHandler,
        Guard,
        LifeCycleHandler,
        Middleware,
    )


try:
    from requests.models import RequestEncodingMixin
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.testing, install starlite with 'testing' extra, e.g. `pip install starlite[testing]`"
    ) from e

__all__ = [
    "TestClient",
    "create_test_client",
    "create_test_request",
]


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


T_client = TypeVar("T_client", bound="TestClient")


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

    def __enter__(self: T_client, *args: Any, **kwargs: Any) -> T_client:
        """
        Starlette's `TestClient.__enter__()` return value is strongly typed to return their own
        `TestClient`, i.e., not-generic to support subclassing.

        We override here to provide a nicer typing experience for our users.

        Parameters
        ----------
        args : Any
        kwargs : Any
            `*args, **kwargs` passed straight through to `Starlette.testing.TestClient.__enter__()`

        Returns
        -------
        TestClient
        """
        return super().__enter__(*args, **kwargs)  # type:ignore[return-value]


def create_test_client(
    route_handlers: Union[
        Union["Type[Controller]", "BaseRouteHandler", "Router", "AnyCallable"],
        List[Union["Type[Controller]", "BaseRouteHandler", "Router", "AnyCallable"]],
    ],
    *,
    after_request: Optional["AfterRequestHandler"] = None,
    after_response: Optional["AfterResponseHandler"] = None,
    allowed_hosts: Optional[List[str]] = None,
    backend: str = "asyncio",
    backend_options: Optional[Dict[str, Any]] = None,
    base_url: str = "http://testserver",
    before_request: Optional["BeforeRequestHandler"] = None,
    cache_config: "CacheConfig" = DEFAULT_CACHE_CONFIG,
    compression_config: Optional["CompressionConfig"] = None,
    cors_config: Optional["CORSConfig"] = None,
    dependencies: Optional[Dict[str, "Provide"]] = None,
    exception_handlers: Optional[Dict[Union[int, "Type[Exception]"], "ExceptionHandler"]] = None,
    guards: Optional[List["Guard"]] = None,
    middleware: Optional[List["Middleware"]] = None,
    on_shutdown: Optional[List["LifeCycleHandler"]] = None,
    on_startup: Optional[List["LifeCycleHandler"]] = None,
    openapi_config: Optional["OpenAPIConfig"] = None,
    parameters: Optional[Dict[str, "FieldInfo"]] = None,
    plugins: Optional[List["PluginProtocol"]] = None,
    raise_server_exceptions: bool = True,
    root_path: str = "",
    static_files_config: Optional[Union["StaticFilesConfig", List["StaticFilesConfig"]]] = None,
    template_config: Optional["TemplateConfig"] = None,
) -> TestClient:
    """Create a TestClient"""
    return TestClient(
        app=Starlite(
            after_request=after_request,
            after_response=after_response,
            allowed_hosts=allowed_hosts,
            before_request=before_request,
            cache_config=cache_config,
            compression_config=compression_config,
            cors_config=cors_config,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            middleware=middleware,
            on_shutdown=on_shutdown,
            on_startup=on_startup,
            openapi_config=openapi_config,
            parameters=parameters,
            plugins=plugins,
            route_handlers=cast("Any", route_handlers if isinstance(route_handlers, list) else [route_handlers]),
            static_files_config=static_files_config,
            template_config=template_config,
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
        headers[ParamType.COOKIE] = cookie
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
