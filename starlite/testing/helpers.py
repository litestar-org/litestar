from typing import TYPE_CHECKING, Any, Literal, Mapping, Optional, Sequence, Type, Union

from starlite.app import DEFAULT_CACHE_CONFIG, Starlite
from starlite.controller import Controller
from starlite.events import SimpleEventEmitter
from starlite.plugins import PluginProtocol
from starlite.testing.client import AsyncTestClient, TestClient
from starlite.utils.predicates import is_class_and_subclass

if TYPE_CHECKING:
    from starlite import Request, SerializationPluginProtocol, WebSocket
    from starlite.config import (
        AllowedHostsConfig,
        BaseLoggingConfig,
        CacheConfig,
        CompressionConfig,
        CORSConfig,
        CSRFConfig,
        OpenAPIConfig,
        StaticFilesConfig,
        TemplateConfig,
    )
    from starlite.events import BaseEventEmitterBackend, EventListener
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
        InitialStateType,
        LifeSpanHandler,
        LifeSpanHookHandler,
        Middleware,
        OnAppInitHandler,
        OptionalSequence,
        ParametersMap,
        ResponseType,
    )


def create_test_client(
    route_handlers: Optional[Union["ControllerRouterHandler", Sequence["ControllerRouterHandler"]]] = None,
    after_exception: "OptionalSequence[AfterExceptionHookHandler]" = None,
    after_request: Optional["AfterRequestHookHandler"] = None,
    after_response: Optional["AfterResponseHookHandler"] = None,
    after_shutdown: "OptionalSequence[LifeSpanHookHandler]" = None,
    after_startup: "OptionalSequence[LifeSpanHookHandler]" = None,
    allowed_hosts: Optional[Union[Sequence[str], "AllowedHostsConfig"]] = None,
    backend: Literal["asyncio", "trio"] = "asyncio",
    backend_options: Optional[Mapping[str, Any]] = None,
    base_url: str = "http://testserver.local",
    before_request: Optional["BeforeRequestHookHandler"] = None,
    before_send: "OptionalSequence[BeforeMessageSendHookHandler]" = None,
    before_shutdown: "OptionalSequence[LifeSpanHookHandler]" = None,
    before_startup: "OptionalSequence[LifeSpanHookHandler]" = None,
    cache_config: "CacheConfig" = DEFAULT_CACHE_CONFIG,
    compression_config: Optional["CompressionConfig"] = None,
    cors_config: Optional["CORSConfig"] = None,
    csrf_config: Optional["CSRFConfig"] = None,
    dependencies: Optional["Dependencies"] = None,
    event_emitter_backend: Type["BaseEventEmitterBackend"] = SimpleEventEmitter,
    exception_handlers: Optional["ExceptionHandlersMap"] = None,
    guards: "OptionalSequence[Guard]" = None,
    initial_state: Optional["InitialStateType"] = None,
    listeners: "OptionalSequence[EventListener]" = None,
    logging_config: Optional["BaseLoggingConfig"] = None,
    middleware: "OptionalSequence[Middleware]" = None,
    on_app_init: "OptionalSequence[OnAppInitHandler]" = None,
    on_shutdown: "OptionalSequence[LifeSpanHandler]" = None,
    on_startup: "OptionalSequence[LifeSpanHandler]" = None,
    openapi_config: Optional["OpenAPIConfig"] = None,
    parameters: Optional["ParametersMap"] = None,
    plugins: "OptionalSequence[PluginProtocol]" = None,
    raise_server_exceptions: bool = True,
    request_class: Optional[Type["Request"]] = None,
    response_class: Optional["ResponseType"] = None,
    root_path: str = "",
    session_config: Optional["BaseBackendConfig"] = None,
    static_files_config: "OptionalSequence[StaticFilesConfig]" = None,
    template_config: Optional["TemplateConfig"] = None,
    websocket_class: Optional[Type["WebSocket"]] = None,
) -> TestClient["Starlite"]:
    """Create a Starlite app instance and initializes it.

    :class:`TestClient <starlite.testing.TestClient>` with it.

    Notes:
        - This function should be called as a context manager to ensure async startup and shutdown are
            handled correctly.

    Examples:
        .. code-block: python

            from starlite import get, create_test_client


            @get("/some-path")
            def my_handler() -> dict[str, str]:
                return {"hello": "world"}


            def test_my_handler() -> None:
                with create_test_client(my_handler) as client:
                    response == client.get("/some-path")
                    assert response.json() == {"hello": "world"}


    Args:
        route_handlers: A single handler or a sequence of route handlers, which can include instances of
            :class:`Router <starlite.router.Router>`, subclasses of :class:`Controller <starlite.controller.Controller>` or
            any function decorated by the route handler decorators.
        after_exception: A sequence of :class:`exception hook handlers <starlite.types.AfterExceptionHookHandler>`.
            This hook is called after an exception occurs. In difference to exception handlers, it is not meant to
            return a response - only to process the exception (e.g. log it, send it to Sentry etc.).
        after_request: A sync or async function executed after the route handler function returned and the response
            object has been resolved. Receives the response object which may be any subclass of
            :class:`Response <starlite.response.Response>`.
        after_response: A sync or async function called after the response has been awaited. It receives the
            :class:`Request <starlite.connection.Request>` object and should not return any values.
        after_shutdown: A sequence of :class:`life-span hook handlers <starlite.types.LifeSpanHookHandler>`.
            This hook is called during the ASGI shutdown, after all callables in the 'on_shutdown' list have been
            called.
        after_startup: A sequence of :class:`life-span hook handlers <starlite.types.LifeSpanHookHandler>`.
            This hook is called during the ASGI startup, after all callables in the 'on_startup' list have been
            called.
        allowed_hosts: A sequence of allowed hosts, or an :class:`allowed hosts config <starlite.config.AllowedHostsConfig>`
            instance. Enables the builtin allowed hosts middleware.
        backend: The async backend to use, options are "asyncio" or "trio".
        backend_options: ``anyio`` options.
        base_url: URL scheme and domain for test request paths, e.g. 'http://testserver'.
        before_request: A sync or async function called immediately before calling the route handler.
            Receives the :class:`Request <starlite.connection.Request>` instance and any non-``None`` return value is
            used for the response, bypassing the route handler.
        before_send: A sequence of :class:`before send hook handlers <starlite.types.BeforeMessageSendHookHandler>`.
            This hook is called when the ASGI send function is called.
        before_shutdown: A sequence of :class:`life-span hook handlers <starlite.types.LifeSpanHookHandler>`.
            This hook is called during the ASGI shutdown, before any 'on_shutdown' hooks are called.
        before_startup: A sequence of :class:`life-span hook handlers <starlite.types.LifeSpanHookHandler>`.
            This hook is called during the ASGI startup, before any 'on_startup' hooks are called.
        cache_config: Configures caching behavior of the application.
        compression_config: Configures compression behaviour of the application, this enabled a builtin or user
            defined Compression middleware.
        cors_config: If set this enables the builtin CORS middleware.
        csrf_config: If set this enables the builtin CSRF middleware.
        dependencies: A string keyed mapping of dependency :class:`Provider <starlite.datastructures.Provide>` instances.
        event_emitter_backend: A subclass of :class:`BaseEventEmitterBackend <starlite.events.emitter.BaseEventEmitterBackend>`.
        exception_handlers: A mapping of status codes and/or exception types to handler functions.
        guards: A sequence of :class:`Guard <starlite.types.Guard>` callables.
        initial_state: An object from which to initialize the app state.
        listeners: A sequence of :class:`EventListener <starlite.events.listener.EventListener>`.
        logging_config: A subclass of :class:`BaseLoggingConfig <starlite.config.logging.BaseLoggingConfig>`.
        middleware: A sequence of :class:`Middleware <starlite.types.Middleware>`.
        on_app_init:  A sequence of :class:`OnAppInitHandler <starlite.types.OnAppInitHandler>` instances. Handlers receive
            an instance of :class:`AppConfig <starlite.config.app.AppConfig>` that will have been initially populated with
            the parameters passed to :class:`Starlite <starlite.app.Starlite>`, and must return an instance of same. If more
            than one handler is registered they are called in the order they are provided.
        on_shutdown: A sequence of :class:`LifeSpanHandler <starlite.types.LifeSpanHandler>` called during
            application shutdown.
        on_startup: A sequence of :class:`LifeSpanHandler <starlite.types.LifeSpanHandler>` called during
            application startup.
        openapi_config: Defaults to :attr:`DEFAULT_OPENAPI_CONFIG <starlite.app.DEFAULT_OPENAPI_CONFIG>`
        parameters: A mapping of :class:`Parameter <starlite.params.Parameter>` definitions available to all
            application paths.
        plugins: Sequence of plugins.
        request_class: An optional subclass of :class:`Request <starlite.connection.request.Request>` to use for
            http connections.
        raise_server_exceptions: Flag for underlying the test client to raise server exceptions instead of
            wrapping them in an HTTP response.
        response_class: A custom subclass of [starlite.response.Response] to be used as the app's default response.
        root_path: Path prefix for requests.
        static_files_config: A sequence of :class:`StaticFilesConfig <starlite.config.StaticFilesConfig>`
        session_config: Configuration for Session Middleware class to create raw session cookies for request to the
            route handlers.
        template_config: An instance of :class:`TemplateConfig <starlite.config.TemplateConfig>`
        websocket_class: An optional subclass of :class:`WebSocket <starlite.connection.websocket.WebSocket>` to use for
            websocket connections.

    Returns:
        An instance of :class:`TestClient <starlite.testing.TestClient>` with a created app instance.
    """
    route_handlers = () if route_handlers is None else route_handlers
    if is_class_and_subclass(route_handlers, Controller) or not isinstance(route_handlers, Sequence):
        route_handlers = (route_handlers,)

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
            event_emitter_backend=event_emitter_backend,
            exception_handlers=exception_handlers,
            guards=guards,
            initial_state=initial_state,
            listeners=listeners,
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
            route_handlers=route_handlers,
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


def create_async_test_client(
    route_handlers: Optional[Union["ControllerRouterHandler", Sequence["ControllerRouterHandler"]]] = None,
    after_exception: "OptionalSequence[AfterExceptionHookHandler]" = None,
    after_request: Optional["AfterRequestHookHandler"] = None,
    after_response: Optional["AfterResponseHookHandler"] = None,
    after_shutdown: "OptionalSequence[LifeSpanHookHandler]" = None,
    after_startup: "OptionalSequence[LifeSpanHookHandler]" = None,
    allowed_hosts: Optional[Union[Sequence[str], "AllowedHostsConfig"]] = None,
    backend: Literal["asyncio", "trio"] = "asyncio",
    backend_options: Optional[Mapping[str, Any]] = None,
    base_url: str = "http://testserver.local",
    before_request: Optional["BeforeRequestHookHandler"] = None,
    before_send: "OptionalSequence[BeforeMessageSendHookHandler]" = None,
    before_shutdown: "OptionalSequence[LifeSpanHookHandler]" = None,
    before_startup: "OptionalSequence[LifeSpanHookHandler]" = None,
    cache_config: "CacheConfig" = DEFAULT_CACHE_CONFIG,
    compression_config: Optional["CompressionConfig"] = None,
    cors_config: Optional["CORSConfig"] = None,
    csrf_config: Optional["CSRFConfig"] = None,
    dependencies: Optional["Dependencies"] = None,
    event_emitter_backend: Type["BaseEventEmitterBackend"] = SimpleEventEmitter,
    exception_handlers: Optional["ExceptionHandlersMap"] = None,
    guards: "OptionalSequence[Guard]" = None,
    initial_state: Optional["InitialStateType"] = None,
    listeners: "OptionalSequence[EventListener]" = None,
    logging_config: Optional["BaseLoggingConfig"] = None,
    middleware: "OptionalSequence[Middleware]" = None,
    on_app_init: "OptionalSequence[OnAppInitHandler]" = None,
    on_shutdown: "OptionalSequence[LifeSpanHandler]" = None,
    on_startup: "OptionalSequence[LifeSpanHandler]" = None,
    openapi_config: Optional["OpenAPIConfig"] = None,
    parameters: Optional["ParametersMap"] = None,
    plugins: "OptionalSequence[SerializationPluginProtocol]" = None,
    raise_server_exceptions: bool = True,
    request_class: Optional[Type["Request"]] = None,
    response_class: Optional["ResponseType"] = None,
    root_path: str = "",
    session_config: Optional["BaseBackendConfig"] = None,
    static_files_config: "OptionalSequence[StaticFilesConfig]" = None,
    template_config: Optional["TemplateConfig"] = None,
    websocket_class: Optional[Type["WebSocket"]] = None,
) -> AsyncTestClient["Starlite"]:
    """Create a Starlite app instance and initializes it.

    :class:`TestClient <starlite.testing.TestClient>` with it.

    Notes:
        - This function should be called as a context manager to ensure async startup and shutdown are
            handled correctly.

    Examples:
        .. code-block: python

            from starlite import get, create_test_client


            @get("/some-path")
            def my_handler() -> dict[str, str]:
                return {"hello": "world"}


            def test_my_handler() -> None:
                with create_test_client(my_handler) as client:
                    response == client.get("/some-path")
                    assert response.json() == {"hello": "world"}

    Args:
        route_handlers: A single handler or a sequence of route handlers, which can include instances of
            :class:`Router <starlite.router.Router>`, subclasses of :class:`Controller <starlite.controller.Controller>` or
            any function decorated by the route handler decorators.
        after_exception: A sequence of :class:`exception hook handlers <starlite.types.AfterExceptionHookHandler>`.
            This hook is called after an exception occurs. In difference to exception handlers, it is not meant to
            return a response - only to process the exception (e.g. log it, send it to Sentry etc.).
        after_request: A sync or async function executed after the route handler function returned and the response
            object has been resolved. Receives the response object which may be any subclass of
            :class:`Response <starlite.response.Response>`.
        after_response: A sync or async function called after the response has been awaited. It receives the
            :class:`Request <starlite.connection.Request>` object and should not return any values.
        after_shutdown: A sequence of :class:`life-span hook handlers <starlite.types.LifeSpanHookHandler>`.
            This hook is called during the ASGI shutdown, after all callables in the 'on_shutdown' list have been
            called.
        after_startup: A sequence of :class:`life-span hook handlers <starlite.types.LifeSpanHookHandler>`.
            This hook is called during the ASGI startup, after all callables in the 'on_startup' list have been
            called.
        allowed_hosts: A sequence of allowed hosts, or an :class:`allowed hosts config <starlite.config.AllowedHostsConfig>`
            instance. Enables the builtin allowed hosts middleware.
        backend: The async backend to use, options are "asyncio" or "trio".
        backend_options: ``anyio`` options.
        base_url: URL scheme and domain for test request paths, e.g. 'http://testserver'.
        before_request: A sync or async function called immediately before calling the route handler.
            Receives the :class:`Request <starlite.connection.Request>` instance and any non-``None`` return value is
            used for the response, bypassing the route handler.
        before_send: A sequence of :class:`before send hook handlers <starlite.types.BeforeMessageSendHookHandler>`.
            This hook is called when the ASGI send function is called.
        before_shutdown: A sequence of :class:`life-span hook handlers <starlite.types.LifeSpanHookHandler>`.
            This hook is called during the ASGI shutdown, before any 'on_shutdown' hooks are called.
        before_startup: A sequence of :class:`life-span hook handlers <starlite.types.LifeSpanHookHandler>`.
            This hook is called during the ASGI startup, before any 'on_startup' hooks are called.
        cache_config: Configures caching behavior of the application.
        compression_config: Configures compression behaviour of the application, this enabled a builtin or user
            defined Compression middleware.
        cors_config: If set this enables the builtin CORS middleware.
        csrf_config: If set this enables the builtin CSRF middleware.
        dependencies: A string keyed mapping of dependency :class:`Provider <starlite.datastructures.Provide>` instances.
        event_emitter_backend: A subclass of :class:`BaseEventEmitterBackend <starlite.events.emitter.BaseEventEmitterBackend>`.
        exception_handlers: A mapping of status codes and/or exception types to handler functions.
        guards: A sequence of :class:`Guard <starlite.types.Guard>` callables.
        initial_state: An object from which to initialize the app state.
        listeners: A sequence of :class:`EventListener <starlite.events.listener.EventListener>`.
        logging_config: A subclass of :class:`BaseLoggingConfig <starlite.config.logging.BaseLoggingConfig>`.
        middleware: A sequence of :class:`Middleware <starlite.types.Middleware>`.
        on_app_init:  A sequence of :class:`OnAppInitHandler <starlite.types.OnAppInitHandler>` instances. Handlers receive
            an instance of :class:`AppConfig <starlite.config.app.AppConfig>` that will have been initially populated with
            the parameters passed to :class:`Starlite <starlite.app.Starlite>`, and must return an instance of same. If more
            than one handler is registered they are called in the order they are provided.
        on_shutdown: A sequence of :class:`LifeSpanHandler <starlite.types.LifeSpanHandler>` called during
            application shutdown.
        on_startup: A sequence of :class:`LifeSpanHandler <starlite.types.LifeSpanHandler>` called during
            application startup.
        openapi_config: Defaults to :attr:`DEFAULT_OPENAPI_CONFIG <starlite.app.DEFAULT_OPENAPI_CONFIG>`
        parameters: A mapping of :class:`Parameter <starlite.params.Parameter>` definitions available to all
            application paths.
        plugins: Sequence of plugins.
        request_class: An optional subclass of :class:`Request <starlite.connection.request.Request>` to use for
            http connections.
        raise_server_exceptions: Flag for underlying the test client to raise server exceptions instead of
            wrapping them in an HTTP response.
        response_class: A custom subclass of [starlite.response.Response] to be used as the app's default response.
        root_path: Path prefix for requests.
        static_files_config: A sequence of :class:`StaticFilesConfig <starlite.config.StaticFilesConfig>`
        session_config: Configuration for Session Middleware class to create raw session cookies for request to the
            route handlers.
        template_config: An instance of :class:`TemplateConfig <starlite.config.TemplateConfig>`
        websocket_class: An optional subclass of :class:`WebSocket <starlite.connection.websocket.WebSocket>` to use for
            websocket connections.

    Returns:
        An instance of :class:`AsyncTestClient <starlite.testing.AsyncTestClient>` with a created app instance.
    """
    route_handlers = () if route_handlers is None else route_handlers
    if is_class_and_subclass(route_handlers, Controller) or not isinstance(route_handlers, Sequence):
        route_handlers = (route_handlers,)

    return AsyncTestClient[Starlite](
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
            event_emitter_backend=event_emitter_backend,
            exception_handlers=exception_handlers,
            guards=guards,
            initial_state=initial_state,
            listeners=listeners,
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
            route_handlers=route_handlers,
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
