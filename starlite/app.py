from typing import TYPE_CHECKING, Callable, Dict, List, Optional, Union, cast

from starlette.applications import Starlette
from starlette.datastructures import State
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from typing_extensions import Type

from starlite.enums import MediaType
from starlite.exceptions import HTTPException
from starlite.handlers import RouteHandler
from starlite.openapi.config import OpenAPIConfig
from starlite.provide import Provide
from starlite.response import Response
from starlite.routing import RootRouter, Router
from starlite.utils import DeprecatedProperty

if TYPE_CHECKING:  # pragma: no cover
    from starlite.controller import Controller

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig()


# noinspection PyMethodOverriding
class Starlite(Starlette):
    def __init__(  # pylint: disable=super-init-not-called
        self,
        *,
        debug: bool = False,
        middleware: Optional[List[Union[Middleware, BaseHTTPMiddleware]]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], Callable]] = None,
        route_handlers: Optional[List[Union[Type["Controller"], RouteHandler, Router, Callable]]] = None,
        on_startup: Optional[List[Callable]] = None,
        on_shutdown: Optional[List[Callable]] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG
    ):
        self._debug = debug
        self.state = State()
        self.router = RootRouter(
            route_handlers=route_handlers or [],
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            dependencies=dependencies,
            openapi_config=openapi_config,
        )
        self.exception_handlers = {StarletteHTTPException: self.handle_http_exception, **(exception_handlers or {})}
        self.user_middleware = self.set_user_middleware(middleware or [])
        self.middleware_stack = self.build_middleware_stack()

    @staticmethod
    def set_user_middleware(middleware: List[Union[Middleware, BaseHTTPMiddleware]]) -> List[Middleware]:
        """Normalizes the passed in middleware"""
        return [Middleware(cast(Type, m)) if isinstance(m, BaseHTTPMiddleware) else m for m in middleware]

    def register(self, route_handler: Union[Type["Controller"], RouteHandler, Router, Callable]):
        """
        Proxy method for Route.register(**kwargs)
        """
        self.router.register(value=route_handler)

    @staticmethod
    def handle_http_exception(_, exc: Union[HTTPException, StarletteHTTPException]) -> Response:
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

    # these Starlette properties are not supported
    route = DeprecatedProperty()
    add_route = DeprecatedProperty()
    on_event = DeprecatedProperty()
    mount = DeprecatedProperty()
    host = DeprecatedProperty()
    add_middleware = DeprecatedProperty()
    add_exception_handler = DeprecatedProperty()
    add_event_handler = DeprecatedProperty()
    add_websocket_route = DeprecatedProperty()
    websocket_route = DeprecatedProperty()
    middleware = DeprecatedProperty()
