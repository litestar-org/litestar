from typing import Dict, List, Optional, Union, cast

from openapi_schema_pydantic import OpenAPI, Schema
from openapi_schema_pydantic.util import construct_open_api_with_schema_class
from pydantic import Extra, validate_arguments
from pydantic.typing import AnyCallable, NoArgAnyCallable
from starlette.datastructures import State
from starlette.exceptions import ExceptionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from starlette.routing import Router as StarletteRouter
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp, Receive, Scope, Send
from typing_extensions import Type

from starlite.config import CORSConfig, OpenAPIConfig
from starlite.enums import MediaType
from starlite.exceptions import HTTPException
from starlite.handlers import BaseRouteHandler
from starlite.openapi.path_item import create_path_item
from starlite.plugins.base import PluginProtocol
from starlite.provide import Provide
from starlite.request import Request
from starlite.response import Response
from starlite.routing import HTTPRoute, Router
from starlite.types import (
    ControllerRouterHandler,
    ExceptionHandler,
    Guard,
    MiddlewareProtocol,
    ResponseHeader,
)
from starlite.utils import create_function_signature_model

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig(title="Starlite API", version="1.0.0")


class Starlite(Router):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        route_handlers: List[ControllerRouterHandler],
        allowed_hosts: Optional[List[str]] = None,
        cors_config: Optional[CORSConfig] = None,
        debug: bool = False,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]]] = None,
        on_shutdown: Optional[List[NoArgAnyCallable]] = None,
        on_startup: Optional[List[NoArgAnyCallable]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG,
        redirect_slashes: bool = True,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
        plugins: Optional[List[PluginProtocol]] = None
    ):
        self.debug = debug
        self.state = State()
        self.plugins = plugins or []
        super().__init__(
            dependencies=dependencies,
            guards=guards,
            path="",
            response_class=response_class,
            response_headers=response_headers,
            route_handlers=route_handlers,
        )
        self.asgi_router: StarletteRouter = StarletteRouter(
            redirect_slashes=redirect_slashes,
            on_shutdown=on_shutdown or [],
            on_startup=on_startup or [],
            routes=self.routes,
        )
        self.exception_handlers: Dict[Union[int, Type[Exception]], ExceptionHandler] = {
            StarletteHTTPException: self.handle_http_exception,
            **(exception_handlers or {}),
        }
        self.middleware_stack: ASGIApp = self.build_middleware_stack(
            user_middleware=middleware or [], cors_config=cors_config, allowed_hosts=allowed_hosts
        )
        if openapi_config:
            self.openapi_schema = self.create_openapi_schema_model(openapi_config=openapi_config)
            self.register(openapi_config.openapi_controller)
        else:
            self.openapi_schema = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        await self.middleware_stack(scope, receive, send)

    def register(self, value: ControllerRouterHandler) -> None:  # type: ignore[override]
        """
        Register a Controller, Route instance or RouteHandler on the app.

        Calls Router.register() and then creates a signature model for all handlers.
        """
        handlers = super().register(value=value)
        for route_handler in handlers:
            self.create_handler_signature_model(route_handler=route_handler)
        if hasattr(self, "asgi_router"):
            self.asgi_router.routes = self.routes  # type: ignore

    def create_handler_signature_model(self, route_handler: BaseRouteHandler) -> None:
        """
        Creates function signature models for all route handler functions and provider dependencies
        """
        if not route_handler.signature_model:
            route_handler.signature_model = create_function_signature_model(
                fn=cast(AnyCallable, route_handler.fn), plugins=self.plugins
            )
        for provider in list(route_handler.resolve_dependencies().values()):
            if not provider.signature_model:
                provider.signature_model = create_function_signature_model(fn=provider.dependency, plugins=self.plugins)

    def build_middleware_stack(
        self,
        user_middleware: List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]],
        cors_config: Optional[CORSConfig],
        allowed_hosts: Optional[List[str]],
    ) -> ASGIApp:
        """
        Builds the middleware by sandwiching the user middleware between
        the Starlette ExceptionMiddleware and the starlette ServerErrorMiddleware
        """
        current_app: ASGIApp = ExceptionMiddleware(
            app=self.asgi_router, handlers=self.exception_handlers, debug=self.debug
        )
        if allowed_hosts:
            current_app = TrustedHostMiddleware(app=current_app, allowed_hosts=allowed_hosts)
        if cors_config:
            current_app = CORSMiddleware(app=current_app, **cors_config.dict())

        for middleware in user_middleware:
            if isinstance(middleware, Middleware):
                current_app = middleware.cls(app=current_app, **middleware.options)
            else:
                current_app = middleware(app=current_app)
        return ServerErrorMiddleware(
            handler=self.exception_handlers.get(HTTP_500_INTERNAL_SERVER_ERROR, self.handle_http_exception),
            debug=self.debug,
            app=current_app,
        )

    @staticmethod
    def handle_http_exception(_: Request, exc: Exception) -> Response:
        """Default handler for exceptions subclassed from HTTPException"""
        status_code = exc.status_code if isinstance(exc, StarletteHTTPException) else HTTP_500_INTERNAL_SERVER_ERROR
        if isinstance(exc, HTTPException):
            content = {"detail": exc.detail, "extra": exc.extra}
        elif isinstance(exc, StarletteHTTPException):
            content = {"detail": exc.detail}
        else:
            content = {"detail": repr(exc)}
        return Response(
            media_type=MediaType.JSON,
            content=content,
            status_code=status_code,
        )

    def create_openapi_schema_model(self, openapi_config: OpenAPIConfig) -> OpenAPI:
        """
        Updates the OpenAPI schema with all paths registered on the root router
        """
        openapi_schema = openapi_config.to_openapi_schema()
        openapi_schema.paths = {}
        for route in self.routes:
            if (
                isinstance(route, HTTPRoute)
                and any(route_handler.include_in_schema for route_handler in route.route_handler_map.values())
                and (route.path_format or "/") not in openapi_schema.paths
            ):
                openapi_schema.paths[route.path_format or "/"] = create_path_item(
                    route=route, create_examples=openapi_config.create_examples
                )
        # we have to monkey patch the "openapi-schema-pydantic" library, because it doesn't allow extra which causes
        # failures with third party libs such as ormar.
        Schema.Config.extra = Extra.ignore
        return construct_open_api_with_schema_class(openapi_schema)
