from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast
from urllib.parse import urlencode

from orjson import dumps
from pydantic import BaseModel
from starlette.testclient import TestClient as StarletteTestClient

from starlite.app import DEFAULT_CACHE_CONFIG, Starlite
from starlite.connection import Request
from starlite.enums import HttpMethod, ParamType, RequestEncodingType, ScopeType
from starlite.exceptions import MissingDependencyException

if TYPE_CHECKING:
    from typing_extensions import Literal

    from starlite.config import (
        BaseLoggingConfig,
        CacheConfig,
        CompressionConfig,
        CORSConfig,
        CSRFConfig,
        OpenAPIConfig,
        StaticFilesConfig,
        TemplateConfig,
    )
    from starlite.datastructures import Cookie
    from starlite.plugins.base import PluginProtocol
    from starlite.types import (
        AfterExceptionHookHandler,
        AfterRequestHookHandler,
        AfterResponseHookHandler,
        BeforeMessageSendHookHandler,
        BeforeRequestHookHandler,
        ControllerRouterHandler,
        Dependencies,
        ExceptionHandlersMap,
        Guard,
        LifeSpanHandler,
        LifeSpanHookHandler,
        Middleware,
        ParametersMap,
        ResponseType,
        SingleOrList,
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
    "RequestFactory",
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


class TestClient(StarletteTestClient):
    app: Starlite  # type: ignore[assignment]
    """
        Starlite application instance under test.
    """

    def __init__(
        self,
        app: Starlite,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: "Literal['asyncio', 'trio' ]" = "asyncio",
        backend_options: Optional[Dict[str, Any]] = None,
    ) -> None:
        """A client implementation providing a context manager for testing
        applications.

        Args:
            app: The instance of [Starlite][starlite.app.Starlite] under test.
            base_url: URL scheme and domain for test request paths, e.g. 'http://testserver'.
            raise_server_exceptions: Flag for underlying Starlette test client to raise server exceptions instead of
                wrapping them in an HTTP response.
            root_path: Path prefix for requests.
            backend: The async backend to use, options are "asyncio" or "trio".
            backend_options: 'anyio' options.
        """
        super().__init__(
            app=app,  # type: ignore[arg-type]
            base_url=base_url,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
            backend=backend,
            backend_options=backend_options,
        )

    def __enter__(self, *args: Any, **kwargs: Dict[str, Any]) -> "TestClient":
        """Starlette's `TestClient.__enter__()` return value is strongly typed
        to return their own `TestClient`, i.e., not-generic to support
        subclassing.

        We override here to provide a nicer typing experience for our users.

        Args:
            *args : Any
            **kwargs : Any
                `*args, **kwargs` passed straight through to `Starlette.testing.TestClient.__enter__()`

        Returns:
            TestClient
        """
        return super().__enter__(*args, **kwargs)  # type:ignore[return-value]


def create_test_client(
    route_handlers: Union["ControllerRouterHandler", List["ControllerRouterHandler"]],
    *,
    after_exception: Optional["SingleOrList[AfterExceptionHookHandler]"] = None,
    after_request: Optional["AfterRequestHookHandler"] = None,
    after_response: Optional["AfterResponseHookHandler"] = None,
    after_shutdown: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
    after_startup: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
    allowed_hosts: Optional[List[str]] = None,
    backend: "Literal['asyncio', 'trio']" = "asyncio",
    backend_options: Optional[Dict[str, Any]] = None,
    base_url: str = "http://testserver",
    before_request: Optional["BeforeRequestHookHandler"] = None,
    before_send: Optional["SingleOrList[BeforeMessageSendHookHandler]"] = None,
    before_shutdown: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
    before_startup: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
    cache_config: "CacheConfig" = DEFAULT_CACHE_CONFIG,
    compression_config: Optional["CompressionConfig"] = None,
    cors_config: Optional["CORSConfig"] = None,
    csrf_config: Optional["CSRFConfig"] = None,
    dependencies: Optional["Dependencies"] = None,
    exception_handlers: Optional["ExceptionHandlersMap"] = None,
    guards: Optional[List["Guard"]] = None,
    logging_config: Optional["BaseLoggingConfig"] = None,
    middleware: Optional[List["Middleware"]] = None,
    on_shutdown: Optional[List["LifeSpanHandler"]] = None,
    on_startup: Optional[List["LifeSpanHandler"]] = None,
    openapi_config: Optional["OpenAPIConfig"] = None,
    parameters: Optional["ParametersMap"] = None,
    plugins: Optional[List["PluginProtocol"]] = None,
    raise_server_exceptions: bool = True,
    response_class: Optional["ResponseType"] = None,
    root_path: str = "",
    static_files_config: Optional[Union["StaticFilesConfig", List["StaticFilesConfig"]]] = None,
    template_config: Optional["TemplateConfig"] = None,
) -> TestClient:
    """Creates a Starlite app instance and initializes a.

    [TestClient][starlite.testing.TestClient] with it.

    Notes:
        - This function should be called as a context manager to ensure async startup and shutdown are
            handled correctly.

    Examples:

        ```python
        from starlite import get, create_test_client


        @get("/some-path")
        def my_handler() -> dict[str, str]:
            return {"hello": "world"}


        def test_my_handler() -> None:
            with create_test_client(my_handler) as client:
                response == client.get("/some-path")
                assert response.json() == {"hello": "world"}
        ```

    Args:
        route_handlers: A single handler or a list of route handlers, which can include instances of
            [Router][starlite.router.Router], subclasses of [Controller][starlite.controller.Controller] or
            any function decorated by the route handler decorators.
        after_exception: An application level [exception event handler][starlite.types.AfterExceptionHookHandler].
            This hook is called after an exception occurs. In difference to exception handlers, it is not meant to
            return a response - only to process the exception (e.g. log it, send it to Sentry etc.).
        after_request: A sync or async function executed after the route handler function returned and the response
            object has been resolved. Receives the response object which may be either an instance of
            [Response][starlite.response.Response] or `starlette.Response`.
        after_response: A sync or async function called after the response has been awaited. It receives the
            [Request][starlite.connection.Request] object and should not return any values.
        after_shutdown: An application level [LifeSpan hook handler][starlite.types.LifeSpanHookHandler].
            This hook is called during the ASGI shutdown, after all callables in the 'on_shutdown'
            list have been called.
        after_startup: An application level [LifeSpan hook handler][starlite.types.LifeSpanHookHandler].
            This hook is called during the ASGI startup, after all callables in the 'on_startup'
            list have been called.
        allowed_hosts: A list of allowed hosts - enables the builtin allowed hosts middleware.
        backend: The async backend to use, options are "asyncio" or "trio".
        backend_options: 'anyio' options.
        base_url: URL scheme and domain for test request paths, e.g. 'http://testserver'.
        before_request: A sync or async function called immediately before calling the route handler.
            Receives the [Request][starlite.connection.Request] instance and any non-`None` return value is
            used for the response, bypassing the route handler.
        before_send: An application level [before send hook handler][starlite.types.BeforeMessageSendHookHandler] or
            list thereof. This hook is called when the ASGI send function is called.
        before_shutdown: An application level [LifeSpan hook handler][starlite.types.LifeSpanHookHandler]. This hook is
            called during the ASGI shutdown, before any callables in the 'on_shutdown' list have been called.
        before_startup: An application level [LifeSpan hook handler][starlite.types.LifeSpanHookHandler]. This hook is
            called during the ASGI startup, before any callables in the 'on_startup' list have been called.
        cache_config: Configures caching behavior of the application.
        compression_config: Configures compression behaviour of the application, this enabled a builtin or user
            defined Compression middleware.
        cors_config: If set this enables the builtin CORS middleware.
        csrf_config: If set this enables the builtin CSRF middleware.
        dependencies: A string keyed dictionary of dependency [Provider][starlite.provide.Provide] instances.
        exception_handlers: A dictionary that maps handler functions to status codes and/or exception types.
        guards: A list of [Guard][starlite.types.Guard] callables.
        logging_config: A subclass of [BaseLoggingConfig][starlite.config.logging.BaseLoggingConfig].
        middleware: A list of [Middleware][starlite.types.Middleware].
        on_shutdown: A list of [LifeSpanHandler][starlite.types.LifeSpanHandler] called during
            application shutdown.
        on_startup: A list of [LifeSpanHandler][starlite.types.LifeSpanHandler] called during
            application startup.
        openapi_config: Defaults to [DEFAULT_OPENAPI_CONFIG][starlite.app.DEFAULT_OPENAPI_CONFIG]
        parameters: A mapping of [Parameter][starlite.params.Parameter] definitions available to all
            application paths.
        plugins: List of plugins.
        raise_server_exceptions: Flag for underlying Starlette test client to raise server exceptions instead of
            wrapping them in an HTTP response.
        response_class: A custom subclass of [starlite.response.Response] to be used as the app's default response.
        root_path: Path prefix for requests.
        static_files_config: An instance or list of [StaticFilesConfig][starlite.config.StaticFilesConfig]
        template_config: An instance of [TemplateConfig][starlite.config.TemplateConfig]

    Returns:
        An instance of [TestClient][starlite.testing.TestClient] with a created app instance.
    """
    return TestClient(
        app=Starlite(
            after_exception=after_exception,
            after_request=after_request,
            after_response=after_response,
            after_shutdown=after_shutdown,
            after_startup=after_startup,
            allowed_hosts=allowed_hosts,
            before_request=before_request,
            before_send=before_send,
            before_shutdown=before_shutdown,
            before_startup=before_startup,
            cache_config=cache_config,
            compression_config=compression_config,
            cors_config=cors_config,
            csrf_config=csrf_config,
            dependencies=dependencies,
            exception_handlers=exception_handlers,
            guards=guards,
            logging_config=logging_config,
            middleware=middleware,
            on_shutdown=on_shutdown,
            on_startup=on_startup,
            openapi_config=openapi_config,
            parameters=parameters,
            plugins=plugins,
            response_class=response_class,
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


class RequestFactory:
    def __init__(
        self,
        app: Starlite = Starlite(route_handlers=[]),
        server: str = "test.org",
        port: int = 3000,
        root_path: str = "",
        scheme: str = "http",
    ) -> None:
        """A factory object to create [Request][starlite.connection.Request]
        instances.

        Args:
             app: An instance of [Starlite][starlite.app.Starlite] to set as `request.scope["app"]`.
             server: The server's domain.
             port: The server's port.
             root_path: Root path for the server.
             scheme: Scheme for the server.

        Examples:

        ```python
        from starlite import RequestEncodingType, Starlite
        from starlite.testing import RequestFactory

        from tests import PersonFactory

        my_app = Starlite(route_handlers=[])
        my_server = "starlite.org"

        # Create a GET request
        query_params = {"id": 1}
        get_user_request = RequestFactory(app=my_app, server=my_server).get(
            "/person", query_params=query_params
        )

        # Create a POST request
        new_person = PersonFactory.build()
        create_user_request = RequestFactory(app=my_app, server=my_server).post(
            "/person", data=person
        )

        # Create a request with a special header
        headers = {"header1": "value1"}
        request_with_header = RequestFactory(app=my_app, server=my_server).get(
            "/person", query_params=query_params, headers=headers
        )

        # Create a request with a media type
        request_with_media_type = RequestFactory(app=my_app, server=my_server).post(
            "/person", data=person, request_media_type=RequestEncodingType.MULTI_PART
        )
        ```
        """

        self.app = app
        self.server = server
        self.port = port
        self.root_path = root_path
        self.scheme = scheme

    def _create_scope(
        self,
        path: str,
        http_method: HttpMethod,
        session: Optional[Dict[str, Any]] = None,
        user: Any = None,
        auth: Any = None,
    ) -> Dict[str, Any]:
        """Create the scope for the [Request][starlite.connection.Request].

        Args:
            path: The request's path.
            http_method: The request's HTTP method.
            session: A dictionary of session data.
            user: A value for `request.scope["user"]`
            auth: A value for `request.scope["auth"]`
        Returns:
            A dictionary that can be passed as a scope to the [Request][starlite.connection.Request] c'tor.
        """

        return dict(
            type=ScopeType.HTTP,
            method=http_method,
            scheme=self.scheme,
            server=(self.server, self.port),
            root_path=self.root_path.rstrip("/"),
            path=path,
            headers=[],
            app=self.app,
            session=session,
            user=user,
            auth=auth,
        )

    @classmethod
    def _create_cookie_header(
        cls, headers: Dict[str, str], cookies: Optional[Union[List["Cookie"], str]] = None
    ) -> None:
        """Create the cookie header and add it to the `headers` dictionary.

        Args:
            headers: A dictionary of headers, the cookie header will be added to it.
            cookies: A string representing the cookie header or a list of "Cookie" instances.
                This value can include multiple cookies.
        """

        if not cookies:
            return None

        if isinstance(cookies, list):
            cookie_header = "; ".join(cookie.to_header(header="") for cookie in cookies)
            headers[ParamType.COOKIE] = cookie_header
        elif isinstance(cookies, str):
            headers[ParamType.COOKIE] = cookies

    def _build_headers(
        self,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Union[List["Cookie"], str]] = None,
    ) -> List[Tuple[bytes, bytes]]:
        """Build a list of encoded headers that can be passed to the request
        scope.

        Args:
            headers: A dictionary of headers.
            cookies: A string representing the cookie header or a list of "Cookie" instances.
                This value can include multiple cookies.
        Returns:
            A list of encoded headers that can be passed to the request scope.
        """

        headers = headers or {}
        self._create_cookie_header(headers, cookies)
        return [
            ((key.lower()).encode("latin-1", errors="ignore"), value.encode("latin-1", errors="ignore"))
            for key, value in headers.items()
        ]

    def _create_request_with_data(
        self,
        http_method: HttpMethod,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Union[List["Cookie"], str]] = None,
        session: Optional[Dict[str, Any]] = None,
        user: Any = None,
        auth: Any = None,
        request_media_type: RequestEncodingType = RequestEncodingType.JSON,
        data: Optional[Union[Dict[str, Any], "BaseModel"]] = None,
    ) -> Request[Any, Any]:
        """Create a [Request][starlite.connection.Request] instance that has
        body (data)

        Args:
            http_method: The request's HTTP method.
            path: The request's path.
            headers: A dictionary of headers.
            cookies: A string representing the cookie header or a list of "Cookie" instances.
                This value can include multiple cookies.
            session: A dictionary of session data.
            user: A value for `request.scope["user"]`
            auth: A value for `request.scope["auth"]`
            request_media_type: The 'Content-Type' header of the request.
            data: A value for the request's body. Can be either a pydantic model instance
                or a string keyed dictionary.
        Returns:
            A [Request][starlite.connection.Request] instance
        """

        scope = self._create_scope(path, http_method, session, user, auth)

        headers = headers or {}
        if data:
            if isinstance(data, BaseModel):
                data = data.dict()
            if request_media_type == RequestEncodingType.JSON:
                body = dumps(data)
                headers["Content-Type"] = str(RequestEncodingType.JSON.value)
            elif request_media_type == RequestEncodingType.MULTI_PART:
                body, content_type = RequestEncoder().multipart_encode(data)
                headers["Content-Type"] = content_type
            else:
                body = RequestEncoder().url_encode(data)
                headers["Content-Type"] = str(RequestEncodingType.URL_ENCODED.value)
            scope["_body"] = body

        self._create_cookie_header(headers, cookies)
        scope["headers"] = self._build_headers(headers)
        return Request(scope=scope)  # type: ignore[arg-type]

    def get(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Union[List["Cookie"], str]] = None,
        session: Optional[Dict[str, Any]] = None,
        user: Any = None,
        auth: Any = None,
        query_params: Optional[Dict[str, Union[str, List[str]]]] = None,
    ) -> Request[Any, Any]:
        """Create a GET [Request][starlite.connection.Request] instance.

        Args:
            path: The request's path.
            headers: A dictionary of headers.
            cookies: A string representing the cookie header or a list of "Cookie" instances.
                This value can include multiple cookies.
            session: A dictionary of session data.
            user: A value for `request.scope["user"]`.
            auth: A value for `request.scope["auth"]`.
            query_params: A dictionary of values from which the request's query will be generated.
        Returns:
            A [Request][starlite.connection.Request] instance
        """

        scope = self._create_scope(path, HttpMethod.GET, session, user, auth)

        if query_params:
            scope["query_string"] = urlencode(query_params, doseq=True).encode()

        scope["headers"] = self._build_headers(headers, cookies)
        return Request(scope=scope)  # type: ignore[arg-type]

    def post(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Union[List["Cookie"], str]] = None,
        session: Optional[Dict[str, Any]] = None,
        user: Any = None,
        auth: Any = None,
        request_media_type: RequestEncodingType = RequestEncodingType.JSON,
        data: Optional[Union[Dict[str, Any], "BaseModel"]] = None,
    ) -> Request[Any, Any]:
        """Create a POST [Request][starlite.connection.Request] instance.

        Args:
            path: The request's path.
            headers: A dictionary of headers.
            cookies: A string representing the cookie header or a list of "Cookie" instances.
                This value can include multiple cookies.
            session: A dictionary of session data.
            user: A value for `request.scope["user"]`.
            auth: A value for `request.scope["auth"]`.
            request_media_type: The 'Content-Type' header of the request.
            data: A value for the request's body. Can be either a pydantic model instance
                or a string keyed dictionary.
        Returns:
            A [Request][starlite.connection.Request] instance
        """

        return self._create_request_with_data(
            HttpMethod.POST,
            path,
            headers,
            cookies,
            session,
            user,
            auth,
            request_media_type,
            data,
        )

    def put(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Union[List["Cookie"], str]] = None,
        session: Optional[Dict[str, Any]] = None,
        user: Any = None,
        auth: Any = None,
        request_media_type: RequestEncodingType = RequestEncodingType.JSON,
        data: Optional[Union[Dict[str, Any], "BaseModel"]] = None,
    ) -> Request[Any, Any]:
        """Create a PUT [Request][starlite.connection.Request] instance.

        Args:
            path: The request's path.
            headers: A dictionary of headers.
            cookies: A string representing the cookie header or a list of "Cookie" instances.
                This value can include multiple cookies.
            session: A dictionary of session data.
            user: A value for `request.scope["user"]`.
            auth: A value for `request.scope["auth"]`.
            request_media_type: The 'Content-Type' header of the request.
            data: A value for the request's body. Can be either a pydantic model instance
                or a string keyed dictionary.
        Returns:
            A [Request][starlite.connection.Request] instance
        """

        return self._create_request_with_data(
            HttpMethod.PUT,
            path,
            headers,
            cookies,
            session,
            user,
            auth,
            request_media_type,
            data,
        )

    def patch(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Union[List["Cookie"], str]] = None,
        session: Optional[Dict[str, Any]] = None,
        user: Any = None,
        auth: Any = None,
        request_media_type: RequestEncodingType = RequestEncodingType.JSON,
        data: Optional[Union[Dict[str, Any], "BaseModel"]] = None,
    ) -> Request[Any, Any]:
        """Create a PATCH [Request][starlite.connection.Request] instance.

        Args:
            path: The request's path.
            headers: A dictionary of headers.
            cookies: A string representing the cookie header or a list of "Cookie" instances.
                This value can include multiple cookies.
            session: A dictionary of session data.
            user: A value for `request.scope["user"]`.
            auth: A value for `request.scope["auth"]`.
            request_media_type: The 'Content-Type' header of the request.
            data: A value for the request's body. Can be either a pydantic model instance
                or a string keyed dictionary.
        Returns:
            A [Request][starlite.connection.Request] instance
        """

        return self._create_request_with_data(
            HttpMethod.PATCH,
            path,
            headers,
            cookies,
            session,
            user,
            auth,
            request_media_type,
            data,
        )

    def delete(
        self,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        cookies: Optional[Union[List["Cookie"], str]] = None,
        session: Optional[Dict[str, Any]] = None,
        user: Any = None,
        auth: Any = None,
    ) -> Request[Any, Any]:
        """Create a POST [Request][starlite.connection.Request] instance.

        Args:
            path: The request's path.
            headers: A dictionary of headers.
            cookies: A string representing the cookie header or a list of "Cookie" instances.
                This value can include multiple cookies.
            session: A dictionary of session data.
            user: A value for `request.scope["user"]`.
            auth: A value for `request.scope["auth"]`.
        Returns:
            A [Request][starlite.connection.Request] instance
        """

        scope = self._create_scope(path, HttpMethod.DELETE, session, user, auth)
        scope["headers"] = self._build_headers(headers, cookies)
        return Request(scope=scope)  # type: ignore[arg-type]


def create_test_request(
    app: Starlite = Starlite(route_handlers=[]),
    auth: Any = None,
    content: Optional[Union[Dict[str, Any], "BaseModel"]] = None,
    cookie: Optional[Union[List["Cookie"], str]] = None,
    headers: Optional[Dict[str, str]] = None,
    http_method: HttpMethod = HttpMethod.GET,
    path: str = "",
    port: int = 3000,
    query: Optional[Dict[str, Union[str, List[str]]]] = None,
    request_media_type: RequestEncodingType = RequestEncodingType.JSON,
    root_path: str = "/",
    scheme: str = "http",
    server: str = "test.org",
    user: Any = None,
) -> Request[Any, Any]:
    """Create a [Request][starlite.connection.Request] instance using the
    passed in parameters.

    Args:
        app: An instance of [Starlite][starlite.app.Starlite] to set as `request.scope["app"]`.
        auth: A value for `request.scope["auth"]`
        content: A value for the request's body. Can be either a pydantic model instance or a string keyed dictionary.
        cookie: A string representing the cookie header or a list of "Cookie" instances. This value can include multiple
            cookies.
        headers: A string / string dictionary of headers.
        http_method: The request's HTTP method.
        path: The request's path.
        port: The request's port.
        query: A string keyed dictionary of values from which the request's query will be generated.
        request_media_type: The 'Content-Type' header of the request.
        root_path: Root path for the server.
        scheme: Scheme for the server.
        server: Domain for the server.
        user: A value for `request.scope["user"]`
    Returns:
        A [Request][starlite.connection.Request] instance.
    """

    request_factory = RequestFactory(
        app=app,
        server=server,
        port=port,
        root_path=root_path,
        scheme=scheme,
    )

    if http_method == HttpMethod.GET:
        return request_factory.get(
            path=path or "/",
            headers=headers,
            cookies=cookie,
            user=user,
            auth=auth,
            query_params=query,
        )
    elif http_method == HttpMethod.POST:
        return request_factory.post(
            path=path or "/",
            headers=headers,
            cookies=cookie,
            user=user,
            auth=auth,
            request_media_type=request_media_type,
            data=content,
        )
    elif http_method == HttpMethod.PUT:
        return request_factory.put(
            path=path or "/",
            headers=headers,
            cookies=cookie,
            user=user,
            auth=auth,
            request_media_type=request_media_type,
            data=content,
        )
    elif http_method == HttpMethod.PATCH:
        return request_factory.patch(
            path=path or "/",
            headers=headers,
            cookies=cookie,
            user=user,
            auth=auth,
            request_media_type=request_media_type,
            data=content,
        )
    elif http_method == HttpMethod.DELETE:
        return request_factory.delete(
            path=path or "/",
            headers=headers,
            cookies=cookie,
            user=user,
            auth=auth,
        )

    raise ValueError(f"Cannot create request for HTTP method {http_method.value}")
