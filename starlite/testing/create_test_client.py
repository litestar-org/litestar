from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    List,
    Literal,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)

from starlite.app import DEFAULT_CACHE_CONFIG, Starlite
from starlite.testing.test_client import TestClient

if TYPE_CHECKING:
    from starlite import (
        BaseLoggingConfig,
        CacheConfig,
        CompressionConfig,
        CORSConfig,
        CSRFConfig,
        OpenAPIConfig,
        PluginProtocol,
        Request,
        StaticFilesConfig,
        TemplateConfig,
        WebSocket,
    )
    from starlite.config import AllowedHostsConfig
    from starlite.datastructures.state import ImmutableState
    from starlite.middleware.session.base import BaseBackendConfig
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
        OnAppInitHandler,
        ParametersMap,
        ResponseType,
        SingleOrList,
    )


def create_test_client(
    route_handlers: Union["ControllerRouterHandler", List["ControllerRouterHandler"]],
    *,
    after_exception: Optional["SingleOrList[AfterExceptionHookHandler]"] = None,
    after_request: Optional["AfterRequestHookHandler"] = None,
    after_response: Optional["AfterResponseHookHandler"] = None,
    after_shutdown: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
    after_startup: Optional["SingleOrList[LifeSpanHookHandler]"] = None,
    allowed_hosts: Optional[Union[List[str], "AllowedHostsConfig"]] = None,
    backend: Literal["asyncio", "trio"] = "asyncio",
    backend_options: Optional[Dict[str, Any]] = None,
    base_url: str = "http://testserver.local",
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
    initial_state: Optional[Union["ImmutableState", Dict[str, Any], Iterable[Tuple[str, Any]]]] = None,
    logging_config: Optional["BaseLoggingConfig"] = None,
    middleware: Optional[List["Middleware"]] = None,
    on_app_init: Optional[List["OnAppInitHandler"]] = None,
    on_shutdown: Optional[List["LifeSpanHandler"]] = None,
    on_startup: Optional[List["LifeSpanHandler"]] = None,
    openapi_config: Optional["OpenAPIConfig"] = None,
    parameters: Optional["ParametersMap"] = None,
    plugins: Optional[List["PluginProtocol"]] = None,
    raise_server_exceptions: bool = True,
    request_class: Optional[Type["Request"]] = None,
    response_class: Optional["ResponseType"] = None,
    root_path: str = "",
    session_config: Optional["BaseBackendConfig"] = None,
    static_files_config: Optional[Union["StaticFilesConfig", List["StaticFilesConfig"]]] = None,
    template_config: Optional["TemplateConfig"] = None,
    websocket_class: Optional[Type["WebSocket"]] = None,
) -> TestClient["Starlite"]:
    """Create a Starlite app instance and initializes it.

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
            object has been resolved. Receives the response object which may be any subclass of
            [Response][starlite.response.Response].
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
        initial_state: An object from which to initialize the app state.
        logging_config: A subclass of [BaseLoggingConfig][starlite.config.logging.BaseLoggingConfig].
        middleware: A list of [Middleware][starlite.types.Middleware].
        on_app_init:  A sequence of [OnAppInitHandler][starlite.types.OnAppInitHandler] instances. Handlers receive
                an instance of [AppConfig][starlite.config.app.AppConfig] that will have been initially populated with
                the parameters passed to [Starlite][starlite.app.Starlite], and must return an instance of same. If more
                than one handler is registered they are called in the order they are provided.
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
        raise_server_exceptions: Flag for underlying the test client to raise server exceptions instead of
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
    return TestClient[Starlite](
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
            initial_state=initial_state,
            logging_config=logging_config,
            middleware=middleware,
            on_app_init=on_app_init,
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
