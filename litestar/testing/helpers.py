from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal, Mapping, Sequence

from litestar.app import DEFAULT_OPENAPI_CONFIG, Litestar
from litestar.controller import Controller
from litestar.events import SimpleEventEmitter
from litestar.testing.client import AsyncTestClient, TestClient
from litestar.types import Empty
from litestar.utils.predicates import is_class_and_subclass

if TYPE_CHECKING:
    from litestar import Request, WebSocket
    from litestar.config.allowed_hosts import AllowedHostsConfig
    from litestar.config.compression import CompressionConfig
    from litestar.config.cors import CORSConfig
    from litestar.config.csrf import CSRFConfig
    from litestar.config.response_cache import ResponseCacheConfig
    from litestar.datastructures import CacheControlHeader, ETag, ResponseHeader, State
    from litestar.dto.interface import DTOInterface
    from litestar.events import BaseEventEmitterBackend, EventListener
    from litestar.logging.config import BaseLoggingConfig
    from litestar.middleware.session.base import BaseBackendConfig
    from litestar.openapi.config import OpenAPIConfig
    from litestar.openapi.spec import SecurityRequirement
    from litestar.plugins import PluginProtocol
    from litestar.static_files.config import StaticFilesConfig
    from litestar.stores.base import Store
    from litestar.stores.registry import StoreRegistry
    from litestar.template.config import TemplateConfig
    from litestar.types import (
        AfterExceptionHookHandler,
        AfterRequestHookHandler,
        AfterResponseHookHandler,
        BeforeMessageSendHookHandler,
        BeforeRequestHookHandler,
        ControllerRouterHandler,
        Dependencies,
        EmptyType,
        ExceptionHandlersMap,
        Guard,
        LifeSpanHandler,
        LifeSpanHookHandler,
        Middleware,
        OnAppInitHandler,
        OptionalSequence,
        ParametersMap,
        ResponseCookies,
        ResponseType,
        TypeEncodersMap,
    )


def create_test_client(
    route_handlers: ControllerRouterHandler | Sequence[ControllerRouterHandler] | None = None,
    *,
    after_exception: OptionalSequence[AfterExceptionHookHandler] = None,
    after_request: AfterRequestHookHandler | None = None,
    after_response: AfterResponseHookHandler | None = None,
    after_shutdown: OptionalSequence[LifeSpanHookHandler] = None,
    after_startup: OptionalSequence[LifeSpanHookHandler] = None,
    allowed_hosts: Sequence[str] | AllowedHostsConfig | None = None,
    backend: Literal["asyncio", "trio"] = "asyncio",
    backend_options: Mapping[str, Any] | None = None,
    base_url: str = "http://testserver.local",
    before_request: BeforeRequestHookHandler | None = None,
    before_send: OptionalSequence[BeforeMessageSendHookHandler] = None,
    before_shutdown: OptionalSequence[LifeSpanHookHandler] = None,
    before_startup: OptionalSequence[LifeSpanHookHandler] = None,
    cache_control: CacheControlHeader | None = None,
    compression_config: CompressionConfig | None = None,
    cors_config: CORSConfig | None = None,
    csrf_config: CSRFConfig | None = None,
    debug: bool = False,
    dependencies: Dependencies | None = None,
    dto: type[DTOInterface] | None | EmptyType = Empty,
    etag: ETag | None = None,
    event_emitter_backend: type[BaseEventEmitterBackend] = SimpleEventEmitter,
    exception_handlers: ExceptionHandlersMap | None = None,
    guards: OptionalSequence[Guard] = None,
    listeners: OptionalSequence[EventListener] = None,
    logging_config: BaseLoggingConfig | EmptyType | None = Empty,
    middleware: OptionalSequence[Middleware] = None,
    multipart_form_part_limit: int = 1000,
    on_app_init: OptionalSequence[OnAppInitHandler] = None,
    on_shutdown: OptionalSequence[LifeSpanHandler] = None,
    on_startup: OptionalSequence[LifeSpanHandler] = None,
    openapi_config: OpenAPIConfig | None = DEFAULT_OPENAPI_CONFIG,
    opt: Mapping[str, Any] | None = None,
    parameters: ParametersMap | None = None,
    plugins: OptionalSequence[PluginProtocol] = None,
    preferred_validation_backend: Literal["pydantic", "attrs"] = "attrs",
    raise_server_exceptions: bool = True,
    request_class: type[Request] | None = None,
    response_cache_config: ResponseCacheConfig | None = None,
    response_class: ResponseType | None = None,
    response_cookies: ResponseCookies | None = None,
    response_headers: OptionalSequence[ResponseHeader] = None,
    return_dto: type[DTOInterface] | None | EmptyType = Empty,
    root_path: str = "",
    security: OptionalSequence[SecurityRequirement] = None,
    session_config: BaseBackendConfig | None = None,
    signature_namespace: Mapping[str, Any] | None = None,
    state: State | None = None,
    static_files_config: OptionalSequence[StaticFilesConfig] = None,
    stores: StoreRegistry | dict[str, Store] | None = None,
    tags: Sequence[str] | None = None,
    template_config: TemplateConfig | None = None,
    type_encoders: TypeEncodersMap | None = None,
    websocket_class: type[WebSocket] | None = None,
) -> TestClient[Litestar]:
    """Create a Litestar app instance and initializes it.

    :class:`TestClient <litestar.testing.TestClient>` with it.

    Notes:
        - This function should be called as a context manager to ensure async startup and shutdown are
            handled correctly.

    Examples:
        .. code-block: python

            from litestar import get
            from litestar.testing import create_test_client

            @get("/some-path")
            def my_handler() -> dict[str, str]:
                return {"hello": "world"}

            def test_my_handler() -> None:
                with create_test_client(my_handler) as client:
                    response == client.get("/some-path")
                    assert response.json() == {"hello": "world"}

    Args:
        preferred_validation_backend:
        route_handlers: A single handler or a sequence of route handlers, which can include instances of
            :class:`Router <litestar.router.Router>`, subclasses of :class:`Controller <.controller.Controller>` or
            any function decorated by the route handler decorators.
        backend: The async backend to use, options are "asyncio" or "trio".
        backend_options: ``anyio`` options.
        base_url: URL scheme and domain for test request paths, e.g. ``http://testserver``.
        raise_server_exceptions: Flag for underlying the test client to raise server exceptions instead of wrapping them
            in an HTTP response.
        root_path: Path prefix for requests.
        session_config: Configuration for Session Middleware class to create raw session cookies for request to the
            route handlers.
        after_exception: A sequence of :class:`exception hook handlers <.types.AfterExceptionHookHandler>`. This
            hook is called after an exception occurs. In difference to exception handlers, it is not meant to
            return a response - only to process the exception (e.g. log it, send it to Sentry etc.).
        after_request: A sync or async function executed after the route handler function returned and the response
            object has been resolved. Receives the response object.
        after_response: A sync or async function called after the response has been awaited. It receives the
            :class:`Request <.connection.Request>` object and should not return any values.
        after_shutdown: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
            the ASGI shutdown, after all callables in the 'on_shutdown' list have been called.
        after_startup: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
            the ASGI startup, after all callables in the 'on_startup' list have been called.
        allowed_hosts: A sequence of allowed hosts, or an
            :class:`AllowedHostsConfig <.config.allowed_hosts.AllowedHostsConfig>` instance. Enables the builtin
            allowed hosts middleware.
        before_request: A sync or async function called immediately before calling the route handler. Receives the
            :class:`Request <.connection.Request>` instance and any non-``None`` return value is used for the
            response, bypassing the route handler.
        before_send: A sequence of :class:`before send hook handlers <.types.BeforeMessageSendHookHandler>`. Called
            when the ASGI send function is called.
        before_shutdown: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
            the ASGI shutdown, before any 'on_shutdown' hooks are called.
        before_startup: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
            the ASGI startup, before any 'on_startup' hooks are called.
        cache_control: A ``cache-control`` header of type
            :class:`CacheControlHeader <litestar.datastructures.CacheControlHeader>` to add to route handlers of
            this app. Can be overridden by route handlers.
        compression_config: Configures compression behaviour of the application, this enabled a builtin or user
            defined Compression middleware.
        cors_config: If set, configures :class:`CORSMiddleware <.middleware.cors.CORSMiddleware>`.
        csrf_config: If set, configures :class:`CSRFMiddleware <.middleware.csrf.CSRFMiddleware>`.
        debug: If ``True``, app errors rendered as HTML with a stack trace.
        dependencies: A string keyed mapping of dependency :class:`Providers <.di.Provide>`.
        dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for (de)serializing and
            validation of request data.
        etag: An ``etag`` header of type :class:`ETag <.datastructures.ETag>` to add to route handlers of this app.
            Can be overridden by route handlers.
        event_emitter_backend: A subclass of
            :class:`BaseEventEmitterBackend <.events.emitter.BaseEventEmitterBackend>`.
        exception_handlers: A mapping of status codes and/or exception types to handler functions.
        guards: A sequence of :class:`Guard <.types.Guard>` callables.
        listeners: A sequence of :class:`EventListener <.events.listener.EventListener>`.
        logging_config: A subclass of :class:`BaseLoggingConfig <.logging.config.BaseLoggingConfig>`.
        middleware: A sequence of :class:`Middleware <.types.Middleware>`.
        multipart_form_part_limit: The maximal number of allowed parts in a multipart/formdata request. This limit
            is intended to protect from DoS attacks.
        on_app_init: A sequence of :class:`OnAppInitHandler <.types.OnAppInitHandler>` instances. Handlers receive
            an instance of :class:`AppConfig <.config.app.AppConfig>` that will have been initially populated with
            the parameters passed to :class:`Litestar <litestar.app.Litestar>`, and must return an instance of same.
            If more than one handler is registered they are called in the order they are provided.
        on_shutdown: A sequence of :class:`LifeSpanHandler <.types.LifeSpanHandler>` called during application
            shutdown.
        on_startup: A sequence of :class:`LifeSpanHandler <litestar.types.LifeSpanHandler>` called during
            application startup.
        openapi_config: Defaults to :attr:`DEFAULT_OPENAPI_CONFIG`
        opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
            wherever you have access to :class:`Request <litestar.connection.request.Request>` or
            :class:`ASGI Scope <.types.Scope>`.
        parameters: A mapping of :class:`Parameter <.params.Parameter>` definitions available to all application
            paths.
        plugins: Sequence of plugins.
        preferred_validation_backend: Validation backend to use, if multiple are installed.
        request_class: An optional subclass of :class:`Request <.connection.Request>` to use for http connections.
        response_class: A custom subclass of :class:`Response <.response.Response>` to be used as the app's default
            response.
        response_cookies: A sequence of :class:`Cookie <.datastructures.Cookie>`.
        response_headers: A string keyed mapping of :class:`ResponseHeader <.datastructures.ResponseHeader>`
        response_cache_config: Configures caching behavior of the application.
        return_dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for serializing
            outbound response data.
        route_handlers: A sequence of route handlers, which can include instances of
            :class:`Router <.router.Router>`, subclasses of :class:`Controller <.controller.Controller>` or any
            callable decorated by the route handler decorators.
        security: A sequence of dicts that will be added to the schema of all route handlers in the application.
            See
            :data:`SecurityRequirement <.openapi.spec.SecurityRequirement>` for details.
        signature_namespace: A mapping of names to types for use in forward reference resolution during signature modelling.
        state: An optional :class:`State <.datastructures.State>` for application state.
        static_files_config: A sequence of :class:`StaticFilesConfig <.static_files.StaticFilesConfig>`
        stores: Central registry of :class:`Store <.stores.base.Store>` that will be available throughout the
            application. If this is a dictionary to it will be passed to a
            :class:`StoreRegistry <.stores.registry.StoreRegistry>`. If it is a
            :class:`StoreRegistry <.stores.registry.StoreRegistry>`, this instance will be used directly.
        tags: A sequence of string tags that will be appended to the schema of all route handlers under the
            application.
        template_config: An instance of :class:`TemplateConfig <.template.TemplateConfig>`
        type_encoders: A mapping of types to callables that transform them into types supported for serialization.
        websocket_class: An optional subclass of :class:`WebSocket <.connection.WebSocket>` to use for websocket
            connections.

    Returns:
        An instance of :class:`TestClient <.testing.TestClient>` with a created app instance.
    """
    route_handlers = () if route_handlers is None else route_handlers
    if is_class_and_subclass(route_handlers, Controller) or not isinstance(route_handlers, Sequence):
        route_handlers = (route_handlers,)

    app = Litestar(
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
        cache_control=cache_control,
        compression_config=compression_config,
        cors_config=cors_config,
        csrf_config=csrf_config,
        debug=debug,
        dependencies=dependencies,
        dto=dto,
        etag=etag,
        event_emitter_backend=event_emitter_backend,
        exception_handlers=exception_handlers,
        guards=guards,
        listeners=listeners,
        logging_config=logging_config,
        middleware=middleware,
        multipart_form_part_limit=multipart_form_part_limit,
        on_app_init=on_app_init,
        on_shutdown=on_shutdown,
        on_startup=on_startup,
        openapi_config=openapi_config,
        opt=opt,
        parameters=parameters,
        plugins=plugins,
        preferred_validation_backend=preferred_validation_backend,
        request_class=request_class,
        response_cache_config=response_cache_config,
        response_class=response_class,
        response_cookies=response_cookies,
        response_headers=response_headers,
        return_dto=return_dto,
        route_handlers=route_handlers,
        security=security,
        signature_namespace=signature_namespace,
        state=state,
        static_files_config=static_files_config,
        stores=stores,
        tags=tags,
        template_config=template_config,
        type_encoders=type_encoders,
        websocket_class=websocket_class,
    )

    return TestClient[Litestar](
        app=app,
        backend=backend,
        backend_options=backend_options,
        base_url=base_url,
        raise_server_exceptions=raise_server_exceptions,
        root_path=root_path,
        session_config=session_config,
    )


def create_async_test_client(
    route_handlers: ControllerRouterHandler | Sequence[ControllerRouterHandler] | None = None,
    *,
    after_exception: OptionalSequence[AfterExceptionHookHandler] = None,
    after_request: AfterRequestHookHandler | None = None,
    after_response: AfterResponseHookHandler | None = None,
    after_shutdown: OptionalSequence[LifeSpanHookHandler] = None,
    after_startup: OptionalSequence[LifeSpanHookHandler] = None,
    allowed_hosts: Sequence[str] | AllowedHostsConfig | None = None,
    backend: Literal["asyncio", "trio"] = "asyncio",
    backend_options: Mapping[str, Any] | None = None,
    base_url: str = "http://testserver.local",
    before_request: BeforeRequestHookHandler | None = None,
    before_send: OptionalSequence[BeforeMessageSendHookHandler] = None,
    before_shutdown: OptionalSequence[LifeSpanHookHandler] = None,
    before_startup: OptionalSequence[LifeSpanHookHandler] = None,
    cache_control: CacheControlHeader | None = None,
    compression_config: CompressionConfig | None = None,
    cors_config: CORSConfig | None = None,
    csrf_config: CSRFConfig | None = None,
    debug: bool = False,
    dependencies: Dependencies | None = None,
    dto: type[DTOInterface] | None | EmptyType = Empty,
    etag: ETag | None = None,
    event_emitter_backend: type[BaseEventEmitterBackend] = SimpleEventEmitter,
    exception_handlers: ExceptionHandlersMap | None = None,
    guards: OptionalSequence[Guard] = None,
    listeners: OptionalSequence[EventListener] = None,
    logging_config: BaseLoggingConfig | EmptyType | None = Empty,
    middleware: OptionalSequence[Middleware] = None,
    multipart_form_part_limit: int = 1000,
    on_app_init: OptionalSequence[OnAppInitHandler] = None,
    on_shutdown: OptionalSequence[LifeSpanHandler] = None,
    on_startup: OptionalSequence[LifeSpanHandler] = None,
    openapi_config: OpenAPIConfig | None = DEFAULT_OPENAPI_CONFIG,
    opt: Mapping[str, Any] | None = None,
    parameters: ParametersMap | None = None,
    plugins: OptionalSequence[PluginProtocol] = None,
    preferred_validation_backend: Literal["pydantic", "attrs"] = "attrs",
    raise_server_exceptions: bool = True,
    request_class: type[Request] | None = None,
    response_cache_config: ResponseCacheConfig | None = None,
    response_class: ResponseType | None = None,
    response_cookies: ResponseCookies | None = None,
    response_headers: OptionalSequence[ResponseHeader] = None,
    return_dto: type[DTOInterface] | None | EmptyType = Empty,
    root_path: str = "",
    security: OptionalSequence[SecurityRequirement] = None,
    session_config: BaseBackendConfig | None = None,
    signature_namespace: Mapping[str, Any] | None = None,
    state: State | None = None,
    static_files_config: OptionalSequence[StaticFilesConfig] = None,
    stores: StoreRegistry | dict[str, Store] | None = None,
    tags: Sequence[str] | None = None,
    template_config: TemplateConfig | None = None,
    type_encoders: TypeEncodersMap | None = None,
    websocket_class: type[WebSocket] | None = None,
) -> AsyncTestClient[Litestar]:
    """Create a Litestar app instance and initializes it.

    :class:`TestClient <litestar.testing.TestClient>` with it.

    Notes:
        - This function should be called as a context manager to ensure async startup and shutdown are
            handled correctly.

    Examples:
        .. code-block: python

            from litestar import get
            from litestar.testing import create_test_client

            @get("/some-path")
            def my_handler() -> dict[str, str]:
                return {"hello": "world"}

            def test_my_handler() -> None:
                with create_test_client(my_handler) as client:
                    response == client.get("/some-path")
                    assert response.json() == {"hello": "world"}

    Args:
        route_handlers: A single handler or a sequence of route handlers, which can include instances of
            :class:`Router <litestar.router.Router>`, subclasses of :class:`Controller <.controller.Controller>` or
            any function decorated by the route handler decorators.
        backend: The async backend to use, options are "asyncio" or "trio".
        backend_options: ``anyio`` options.
        base_url: URL scheme and domain for test request paths, e.g. ``http://testserver``.
        raise_server_exceptions: Flag for underlying the test client to raise server exceptions instead of wrapping them
            in an HTTP response.
        root_path: Path prefix for requests.
        session_config: Configuration for Session Middleware class to create raw session cookies for request to the
            route handlers.
        after_exception: A sequence of :class:`exception hook handlers <.types.AfterExceptionHookHandler>`. This
            hook is called after an exception occurs. In difference to exception handlers, it is not meant to
            return a response - only to process the exception (e.g. log it, send it to Sentry etc.).
        after_request: A sync or async function executed after the route handler function returned and the response
            object has been resolved. Receives the response object.
        after_response: A sync or async function called after the response has been awaited. It receives the
            :class:`Request <.connection.Request>` object and should not return any values.
        after_shutdown: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
            the ASGI shutdown, after all callables in the 'on_shutdown' list have been called.
        after_startup: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
            the ASGI startup, after all callables in the 'on_startup' list have been called.
        allowed_hosts: A sequence of allowed hosts, or an
            :class:`AllowedHostsConfig <.config.allowed_hosts.AllowedHostsConfig>` instance. Enables the builtin
            allowed hosts middleware.
        before_request: A sync or async function called immediately before calling the route handler. Receives the
            :class:`Request <.connection.Request>` instance and any non-``None`` return value is used for the
            response, bypassing the route handler.
        before_send: A sequence of :class:`before send hook handlers <.types.BeforeMessageSendHookHandler>`. Called
            when the ASGI send function is called.
        before_shutdown: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
            the ASGI shutdown, before any 'on_shutdown' hooks are called.
        before_startup: A sequence of :class:`life-span hook handlers <.types.LifeSpanHookHandler>`. Called during
            the ASGI startup, before any 'on_startup' hooks are called.
        cache_control: A ``cache-control`` header of type
            :class:`CacheControlHeader <litestar.datastructures.CacheControlHeader>` to add to route handlers of
            this app. Can be overridden by route handlers.
        compression_config: Configures compression behaviour of the application, this enabled a builtin or user
            defined Compression middleware.
        cors_config: If set, configures :class:`CORSMiddleware <.middleware.cors.CORSMiddleware>`.
        csrf_config: If set, configures :class:`CSRFMiddleware <.middleware.csrf.CSRFMiddleware>`.
        debug: If ``True``, app errors rendered as HTML with a stack trace.
        dependencies: A string keyed mapping of dependency :class:`Providers <.di.Provide>`.
        dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for (de)serializing and
            validation of request data.
        etag: An ``etag`` header of type :class:`ETag <.datastructures.ETag>` to add to route handlers of this app.
            Can be overridden by route handlers.
        event_emitter_backend: A subclass of
            :class:`BaseEventEmitterBackend <.events.emitter.BaseEventEmitterBackend>`.
        exception_handlers: A mapping of status codes and/or exception types to handler functions.
        guards: A sequence of :class:`Guard <.types.Guard>` callables.
        listeners: A sequence of :class:`EventListener <.events.listener.EventListener>`.
        logging_config: A subclass of :class:`BaseLoggingConfig <.logging.config.BaseLoggingConfig>`.
        middleware: A sequence of :class:`Middleware <.types.Middleware>`.
        multipart_form_part_limit: The maximal number of allowed parts in a multipart/formdata request. This limit
            is intended to protect from DoS attacks.
        on_app_init: A sequence of :class:`OnAppInitHandler <.types.OnAppInitHandler>` instances. Handlers receive
            an instance of :class:`AppConfig <.config.app.AppConfig>` that will have been initially populated with
            the parameters passed to :class:`Litestar <litestar.app.Litestar>`, and must return an instance of same.
            If more than one handler is registered they are called in the order they are provided.
        on_shutdown: A sequence of :class:`LifeSpanHandler <.types.LifeSpanHandler>` called during application
            shutdown.
        on_startup: A sequence of :class:`LifeSpanHandler <litestar.types.LifeSpanHandler>` called during
            application startup.
        openapi_config: Defaults to :attr:`DEFAULT_OPENAPI_CONFIG`
        opt: A string keyed mapping of arbitrary values that can be accessed in :class:`Guards <.types.Guard>` or
            wherever you have access to :class:`Request <litestar.connection.request.Request>` or
            :class:`ASGI Scope <.types.Scope>`.
        parameters: A mapping of :class:`Parameter <.params.Parameter>` definitions available to all application
            paths.
        plugins: Sequence of plugins.
        preferred_validation_backend: Validation backend to use, if multiple are installed.
        request_class: An optional subclass of :class:`Request <.connection.Request>` to use for http connections.
        response_class: A custom subclass of :class:`Response <.response.Response>` to be used as the app's default
            response.
        response_cookies: A sequence of :class:`Cookie <.datastructures.Cookie>`.
        response_headers: A string keyed mapping of :class:`ResponseHeader <.datastructures.ResponseHeader>`
        response_cache_config: Configures caching behavior of the application.
        return_dto: :class:`DTOInterface <.dto.interface.DTOInterface>` to use for serializing
            outbound response data.
        route_handlers: A sequence of route handlers, which can include instances of
            :class:`Router <.router.Router>`, subclasses of :class:`Controller <.controller.Controller>` or any
            callable decorated by the route handler decorators.
        security: A sequence of dicts that will be added to the schema of all route handlers in the application.
            See
            :data:`SecurityRequirement <.openapi.spec.SecurityRequirement>` for details.
        signature_namespace: A mapping of names to types for use in forward reference resolution during signature modelling.
        state: An optional :class:`State <.datastructures.State>` for application state.
        static_files_config: A sequence of :class:`StaticFilesConfig <.static_files.StaticFilesConfig>`
        stores: Central registry of :class:`Store <.stores.base.Store>` that will be available throughout the
            application. If this is a dictionary to it will be passed to a
            :class:`StoreRegistry <.stores.registry.StoreRegistry>`. If it is a
            :class:`StoreRegistry <.stores.registry.StoreRegistry>`, this instance will be used directly.
        tags: A sequence of string tags that will be appended to the schema of all route handlers under the
            application.
        template_config: An instance of :class:`TemplateConfig <.template.TemplateConfig>`
        type_encoders: A mapping of types to callables that transform them into types supported for serialization.
        websocket_class: An optional subclass of :class:`WebSocket <.connection.WebSocket>` to use for websocket
            connections.

    Returns:
        An instance of :class:`AsyncTestClient <litestar.testing.AsyncTestClient>` with a created app instance.
    """
    route_handlers = () if route_handlers is None else route_handlers
    if is_class_and_subclass(route_handlers, Controller) or not isinstance(route_handlers, Sequence):
        route_handlers = (route_handlers,)

    app = Litestar(
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
        cache_control=cache_control,
        compression_config=compression_config,
        cors_config=cors_config,
        csrf_config=csrf_config,
        debug=debug,
        dependencies=dependencies,
        dto=dto,
        etag=etag,
        event_emitter_backend=event_emitter_backend,
        exception_handlers=exception_handlers,
        guards=guards,
        listeners=listeners,
        logging_config=logging_config,
        middleware=middleware,
        multipart_form_part_limit=multipart_form_part_limit,
        on_app_init=on_app_init,
        on_shutdown=on_shutdown,
        on_startup=on_startup,
        openapi_config=openapi_config,
        opt=opt,
        parameters=parameters,
        plugins=plugins,
        preferred_validation_backend=preferred_validation_backend,
        request_class=request_class,
        response_cache_config=response_cache_config,
        response_class=response_class,
        response_cookies=response_cookies,
        response_headers=response_headers,
        return_dto=return_dto,
        route_handlers=route_handlers,
        security=security,
        signature_namespace=signature_namespace,
        state=state,
        static_files_config=static_files_config,
        stores=stores,
        tags=tags,
        template_config=template_config,
        type_encoders=type_encoders,
        websocket_class=websocket_class,
    )

    return AsyncTestClient[Litestar](
        app=app,
        backend=backend,
        backend_options=backend_options,
        base_url=base_url,
        raise_server_exceptions=raise_server_exceptions,
        root_path=root_path,
        session_config=session_config,
    )
