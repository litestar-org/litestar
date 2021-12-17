from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    Callable,
    Dict,
    Optional,
    Sequence,
    Union,
)

from starlette.applications import Starlette
from starlette.datastructures import State
from starlette.middleware import Middleware
from typing_extensions import Type

from starlite.handlers import RouteHandler
from starlite.openapi import OpenAPIConfig
from starlite.provide import Provide
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
        middleware: Optional[Sequence[Middleware]] = None,
        exception_handlers: Optional[Dict[Union[int, Type[Exception]], Callable]] = None,
        route_handlers: Optional[Sequence[Union[Type["Controller"], RouteHandler, Router, Callable]]] = None,
        on_startup: Optional[Sequence[Callable]] = None,
        on_shutdown: Optional[Sequence[Callable]] = None,
        lifespan: Optional[Callable[[Any], AsyncContextManager]] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
        openapi_config: Optional[OpenAPIConfig] = DEFAULT_OPENAPI_CONFIG
    ):
        self._debug = debug
        self.state = State()
        self.router = RootRouter(
            route_handlers=route_handlers or [],
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
            dependencies=dependencies,
            openapi_config=openapi_config,
        )
        self.exception_handlers = dict(exception_handlers) if exception_handlers else {}
        self.user_middleware = list(middleware) if middleware else []
        self.middleware_stack = self.build_middleware_stack()

    def register(self, route_handler: Union[Type["Controller"], RouteHandler, Router, Callable]):
        """
        Proxy method for Route.register(**kwargs)
        """
        self.router.register(value=route_handler)

    # these Starlette properties are not supported
    route = DeprecatedProperty()
    add_route = DeprecatedProperty()
