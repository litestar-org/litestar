from typing import TYPE_CHECKING, Dict, List, Optional, Union

from pydantic.typing import AnyCallable, NoArgAnyCallable
from starlette.applications import Starlette
from starlette.datastructures import State
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware import Middleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp
from typing_extensions import Type

from starlite.enums import MediaType
from starlite.exceptions import HTTPException
from starlite.handlers import RouteHandler
from starlite.openapi.config import OpenAPIConfig
from starlite.provide import Provide
from starlite.response import Response
from starlite.routing import RootRouter, Router
from starlite.types import EXCEPTION_HANDLER, ResponseHeader
from starlite.utils import DeprecatedProperty

if TYPE_CHECKING:  # pragma: no cover
    from starlite.controller import Controller

DEFAULT_OPENAPI_CONFIG = OpenAPIConfig()


# noinspection PyMethodOverriding
class Starlite(Starlette):
    def __init__(  # pylint: disable=super-init-not-called
        self,
        *,
        route_handlers: List[Union[Type["Controller"], RouteHandler, Router, AnyCallable]],
        debug: bool = False,
        middleware: Optional[List[Union[Middleware, Type[BaseHTTPMiddleware]]]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], EXCEPTION_HANDLER]] = None,
        on_startup: Optional[List[NoArgAnyCallable]] = None,
        on_shutdown: Optional[List[NoArgAnyCallable]] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG,
        response_headers: Optional[Dict[str, ResponseHeader]] = None
    ):
        self._debug: bool = debug
        self.state: State = State()
        self.router: RootRouter = RootRouter(
            route_handlers=route_handlers or [],
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            dependencies=dependencies,
            openapi_config=openapi_config,
            response_headers=response_headers,
        )
        self.exception_handlers: Dict[Union[int, Type[Exception]], EXCEPTION_HANDLER] = {
            StarletteHTTPException: self.handle_http_exception,
            **(exception_handlers or {}),
        }
        self.user_middleware: List[Middleware] = self.set_user_middleware(middleware or [])
        self.middleware_stack: ASGIApp = self.build_middleware_stack()

    @staticmethod
    def set_user_middleware(middleware: List[Union[Middleware, Type[BaseHTTPMiddleware]]]) -> List[Middleware]:
        """Normalizes the passed in middleware"""
        return [m if isinstance(m, Middleware) else Middleware(m) for m in middleware]

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

    # these Starlette properties are not supported
    route = DeprecatedProperty()  # type: ignore
    add_route = DeprecatedProperty()  # type: ignore
    on_event = DeprecatedProperty()  # type: ignore
    mount = DeprecatedProperty()  # type: ignore
    host = DeprecatedProperty()  # type: ignore
    add_middleware = DeprecatedProperty()  # type: ignore
    add_exception_handler = DeprecatedProperty()  # type: ignore
    add_event_handler = DeprecatedProperty()  # type: ignore
    add_websocket_route = DeprecatedProperty()  # type: ignore
    websocket_route = DeprecatedProperty()  # type: ignore
    middleware = DeprecatedProperty()  # type: ignore
