from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type, Union, cast

from starlette.testclient import TestClient as StarletteTestClient

from starlite.app import DEFAULT_CACHE_CONFIG, Starlite
from starlite.exceptions import MissingDependencyException
from starlite.middleware.session import SessionMiddleware

if TYPE_CHECKING:
    from typing_extensions import Literal

    from starlite import Request, WebSocket
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
    from starlite.middleware.session import SessionCookieConfig
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
    pass
except ImportError as e:
    raise MissingDependencyException(
        "To use starlite.testing, install starlite with 'testing' extra, e.g. `pip install starlite[testing]`"
    ) from e


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
        session_config: Optional["SessionCookieConfig"] = None,
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
            session_config: Configuration for Session Middleware class to create raw session cookies for request to the
                route handlers.
        """
        self.session = SessionMiddleware(app=app, config=session_config) if session_config else None
        super().__init__(
            app=app,  # type: ignore[arg-type]
            base_url=base_url,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
            backend=backend,
            backend_options=backend_options,
        )

    def __enter__(self) -> "TestClient":
        """Starlette's `TestClient.__enter__()` return value is strongly typed
        to return their own `TestClient`, i.e., not-generic to support
        subclassing.

        We override here to provide a nicer typing experience for our user

        Returns:
            TestClient
        """
        return super().__enter__()  # pyright: ignore

    def create_session_cookies(self, session_data: Dict[str, Any]) -> Dict[str, str]:
        """Creates raw session cookies that are loaded into the session by the
        Session Middleware. It creates cookies the same way as if they are
        coming from the browser. Your tests must set up session middleware to
        load raw session cookies into the session.

        Args:
            session_data: Dictionary to create raw session cookies from.

        Returns:
            A dictionary with cookie name as key and cookie value as value.

        Examples:

            ```python
            import pytest
            from starlite.testing import TestClient

            from my_app.main import app, session_cookie_config_instance


            class TestClass:
                @pytest.fixture()
                def test_client(self) -> TestClient:
                    with TestClient(
                        app=app, session_config=session_cookie_config_instance
                    ) as client:
                        yield client

                def test_something(self, test_client: TestClient) -> None:
                    cookies = test_client.create_session_cookies(session_data={"user": "test_user"})
                    # Set raw session cookies to the "cookies" attribute of test_client instance.
                    test_client.cookies = cookies
                    test_client.get(url="/my_route")
            ```
        """
        if self.session is None:
            return {}
        encoded_data = self.session.dump_data(data=session_data)
        return {f"{self.session.config.key}-{i}": chunk.decode("utf-8") for i, chunk in enumerate(encoded_data)}

    def get_session_from_cookies(self) -> Dict[str, Any]:
        """Raw session cookies are a serialized image of session which are
        created by session middleware and sent with the response. To assert
        data in session, this method deserializes the raw session cookies and
        creates session from them.

        Returns:
            A dictionary containing session data.

        Examples:

            ```python
            def test_something(self, test_client: TestClient) -> None:
                test_client.get(url="/my_route")
                session = test_client.get_session_from_cookies()
                assert "user" in session
            ```
        """
        if self.session is None:
            return {}
        raw_data = [self.cookies[key].encode("utf-8") for key in self.cookies if self.session.config.key in key]
        return self.session.load_data(data=raw_data)


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
    request_class: Optional[Type["Request"]] = None,
    response_class: Optional["ResponseType"] = None,
    root_path: str = "",
    session_config: Optional["SessionCookieConfig"] = None,
    static_files_config: Optional[Union["StaticFilesConfig", List["StaticFilesConfig"]]] = None,
    template_config: Optional["TemplateConfig"] = None,
    websocket_class: Optional[Type["WebSocket"]] = None,
) -> TestClient:
    """Creates a Starlite app instance and initializes it.

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
        dependencies: A string keyed dictionary of dependency [Provider][starlite.datastructures.Provide] instances.
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
        request_class: An optional subclass of [Request][starlite.connection.request.Request] to use for
            http connections.
        raise_server_exceptions: Flag for underlying Starlette test client to raise server exceptions instead of
            wrapping them in an HTTP response.
        response_class: A custom subclass of [starlite.response.Response] to be used as the app's default response.
        root_path: Path prefix for requests.
        static_files_config: An instance or list of [StaticFilesConfig][starlite.config.StaticFilesConfig]
        session_config: Configuration for Session Middleware class to create raw session cookies for request to the
            route handlers.
        template_config: An instance of [TemplateConfig][starlite.config.TemplateConfig]
        websocket_class: An optional subclass of [WebSocket][starlite.connection.websocket.WebSocket] to use for
            websocket connections.

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
            request_class=request_class,
            response_class=response_class,
            route_handlers=cast("Any", route_handlers if isinstance(route_handlers, list) else [route_handlers]),
            static_files_config=static_files_config,
            template_config=template_config,
            websocket_class=websocket_class,
        ),
        backend=backend,
        backend_options=backend_options,
        base_url=base_url,
        raise_server_exceptions=raise_server_exceptions,
        root_path=root_path,
        session_config=session_config,
    )
