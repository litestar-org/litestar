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
from starlite.provide import Provide
from starlite.routing import Router
from starlite.utils import DeprecatedProperty

if TYPE_CHECKING:
    from starlite.controller import Controller


# noinspection PyMethodOverriding
class Starlite(Starlette):
    def __init__(  # pylint: disable=super-init-not-called
        self,
        debug: bool = False,
        middleware: Sequence[Middleware] = None,
        exception_handlers: Dict[Union[int, Type[Exception]], Callable] = None,
        route_handlers: Optional[Sequence[Union[Type["Controller"], RouteHandler, Router]]] = None,
        on_startup: Optional[Sequence[Callable]] = None,
        on_shutdown: Optional[Sequence[Callable]] = None,
        lifespan: Optional[Callable[[Any], AsyncContextManager]] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
    ):
        self._debug = debug
        self.state = State()
        self.router = Router(
            path="",
            route_handlers=route_handlers,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
            dependencies=dependencies,
        )
        self.exception_handlers = dict(exception_handlers) if exception_handlers else {}
        self.user_middleware = list(middleware) if middleware else []
        self.middleware_stack = self.build_middleware_stack()

    def register(self, route_handler: RouteHandler):
        """
        Proxy method for Route.register(**kwargs)
        """
        self.router.register(value=route_handler)

    # these Starlette properties are not supported
    route = DeprecatedProperty()
    add_route = DeprecatedProperty()
