from typing import Dict, List, Optional, Union

from openapi_schema_pydantic import OpenAPI
from openapi_schema_pydantic.util import construct_open_api_with_schema_class
from pydantic import validate_arguments
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
from starlite.controller import Controller
from starlite.enums import MediaType
from starlite.exceptions import HTTPException
from starlite.handlers import RouteHandler
from starlite.openapi.path_item import create_path_item
from starlite.provide import Provide
from starlite.request import Request
from starlite.response import Response
from starlite.routing import Router
from starlite.types import ExceptionHandler, Guard, MiddlewareProtocol, ResponseHeader


class Starlite(Router):
    @validate_arguments(config={"arbitrary_types_allowed": True})
    def __init__(
        self,
        *,
        allowed_hosts: Optional[List[str]] = None,
        cors_config: Optional[CORSConfig] = None,
        debug: bool = False,
        dependencies: Optional[Dict[str, Provide]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], ExceptionHandler]] = None,
        guards: Optional[List[Guard]] = None,
        middleware: Optional[List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]]] = None,
        on_shutdown: Optional[List[NoArgAnyCallable]] = None,
        on_startup: Optional[List[NoArgAnyCallable]] = None,
        openapi_config: Optional[OpenAPIConfig] = None,
        redirect_slashes: bool = True,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
        route_handlers: List[Union[Type[Controller], RouteHandler, Router, AnyCallable]],
    ):
        self.debug = debug
        self.state = State()
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
        else:
            self.openapi_schema = None

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        await self.middleware_stack(scope, receive, send)

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
            if route.include_in_schema and (route.path_format or "/") not in openapi_schema.paths:
                openapi_schema.paths[route.path_format or "/"] = create_path_item(
                    route=route, create_examples=openapi_config.create_examples
                )
        return construct_open_api_with_schema_class(openapi_schema)
