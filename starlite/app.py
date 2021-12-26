from typing import TYPE_CHECKING, Dict, List, Optional, Union

from pydantic.typing import AnyCallable, NoArgAnyCallable
from starlette.datastructures import State
from starlette.exceptions import ExceptionMiddleware
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.errors import ServerErrorMiddleware
from starlette.requests import Request
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp, Receive, Scope, Send
from typing_extensions import Type

from starlite.enums import MediaType
from starlite.exceptions import HTTPException
from starlite.handlers import RouteHandler
from starlite.openapi.config import OpenAPIConfig
from starlite.provide import Provide
from starlite.response import Response
from starlite.routing import RootRouter, Router
from starlite.types import EXCEPTION_HANDLER, MiddlewareProtocol, ResponseHeader

if TYPE_CHECKING:  # pragma: no cover
    from starlite.controller import Controller

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig()


class Starlite:
    def __init__(
        self,
        *,
        route_handlers: List[Union[Type["Controller"], RouteHandler, Router, AnyCallable]],
        debug: bool = False,
        middleware: Optional[List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], EXCEPTION_HANDLER]] = None,
        on_startup: Optional[List[NoArgAnyCallable]] = None,
        on_shutdown: Optional[List[NoArgAnyCallable]] = None,
        response_class: Optional[Type[Response]] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG,
        response_headers: Optional[Dict[str, ResponseHeader]] = None
    ):
        self.debug = debug
        self.state: State = State()
        self.router: RootRouter = RootRouter(
            route_handlers=route_handlers or [],
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            dependencies=dependencies,
            openapi_config=openapi_config,
            response_headers=response_headers,
            response_class=response_class,
        )
        self.exception_handlers: Dict[Union[int, Type[Exception]], EXCEPTION_HANDLER] = {
            StarletteHTTPException: self.handle_http_exception,
            **(exception_handlers or {}),
        }
        self.middleware_stack: ASGIApp = self.build_middleware_stack(middleware or [])

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        scope["app"] = self
        await self.middleware_stack(scope, receive, send)

    def build_middleware_stack(
        self, user_middleware: List[Union[Middleware, Type[BaseHTTPMiddleware], Type[MiddlewareProtocol]]]
    ) -> ASGIApp:
        """
        Builds the middleware by sandwiching the user middleware between
        the Starlette ExceptionMiddleware and the starlette ServerErrorMiddleware
        """
        current_app: ASGIApp = ExceptionMiddleware(handlers=self.exception_handlers, debug=self.debug, app=self.router)
        for middleware in user_middleware:
            if isinstance(middleware, Middleware):
                cls, options = middleware
                current_app = cls(app=current_app, **options)
            else:
                current_app = middleware(app=current_app)
        return ServerErrorMiddleware(
            handler=self.exception_handlers.get(HTTP_500_INTERNAL_SERVER_ERROR, self.handle_http_exception),
            debug=self.debug,
            app=current_app,
        )

    @staticmethod
    def handle_http_exception(_: Request, exc: Union[HTTPException, StarletteHTTPException]) -> Response:
        """Default handler for exceptions subclassed from HTTPException"""
        if isinstance(exc, HTTPException):
            content = {"detail": exc.detail, "extra": exc.extra}
        else:
            content = {"detail": exc.detail}
        return Response(
            media_type=MediaType.JSON,
            content=content,
            status_code=exc.status_code,
        )
