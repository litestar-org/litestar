from inspect import isclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, cast

from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route as StarletteRoute
from starlette.routing import Router as StarletteRouter
from starlette.types import ASGIApp
from typing_extensions import AsyncContextManager, Type

from starlite.controller import Controller
from starlite.decorators import RouteHandlerFunction
from starlite.decorators import route as route_decorator
from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.request import handle_request
from starlite.utils.predicates import is_route_handler_function
from starlite.utils.sequence import as_list, find, unique
from starlite.utils.url import join_paths, normalize_path

RouteHandler = Union[Type[Controller], Controller, RouteHandlerFunction, "Router"]


class Route(StarletteRoute):
    route_handler_map: Dict[HttpMethod, RouteHandlerFunction]

    def __init__(
        self,
        *,
        path: str,
        route_handlers: Union[RouteHandlerFunction, Sequence[RouteHandlerFunction]],
    ):
        self.route_handler_map = {}
        name: Optional[str] = None
        include_in_schema = True

        for route_handler in as_list(route_handlers):
            route_info = route_handler.route_info
            for http_method in as_list(route_info.http_method):  # type: ignore
                if self.route_handler_map.get(http_method):
                    raise ImproperlyConfiguredException(
                        f"handler already registered for path {path!r} and http method {http_method}"
                    )
                self.route_handler_map[http_method] = route_handler
                if route_info.name:
                    name = route_info.name
                if route_info.include_in_schema is not None:
                    include_in_schema = route_info.include_in_schema

        super().__init__(
            path=path,
            endpoint=self.create_endpoint_handler(self.route_handler_map),
            name=name,
            include_in_schema=include_in_schema,
            methods=[method.upper() for method in self.route_handler_map],
        )

    @staticmethod
    def create_endpoint_handler(http_handler_mapping: Dict[HttpMethod, RouteHandlerFunction]) -> Callable:
        """
        Create a Starlette endpoint handler given a dictionary mapping of http-methods to RouteHandlers

        Using this method, Starlite is able to support different handler functions for the same path.
        """

        async def endpoint_handler(request: Request) -> Response:
            request_method = HttpMethod.from_str(request.method)
            handler = http_handler_mapping[request_method]
            return await handle_request(route_handler=handler, request=request)

        return endpoint_handler


# noinspection PyMethodOverriding
class Router(StarletteRouter):
    routes: List[Route]

    def __init__(
        self,
        path: str,
        route_handlers: Optional[Sequence[RouteHandler]] = None,
        redirect_slashes: bool = True,
        default: Optional[ASGIApp] = None,
        on_startup: Optional[Sequence[Callable]] = None,
        on_shutdown: Optional[Sequence[Callable]] = None,
        lifespan: Optional[Callable[[Any], AsyncContextManager]] = None,
    ):
        if on_startup or on_shutdown:
            assert not lifespan, "Use either 'lifespan' or 'on_startup'/'on_shutdown', not both."
        self.path = normalize_path(path)
        super().__init__(
            default=default,
            lifespan=lifespan,
            on_shutdown=on_shutdown,
            on_startup=on_startup,
            redirect_slashes=redirect_slashes,
            routes=[],
        )
        for route_handler in route_handlers or []:
            self.register(route_handler=route_handler)

    @property
    def route_handler_method_map(self) -> Dict[str, Dict[HttpMethod, RouteHandlerFunction]]:
        """
        Returns dictionary that maps paths (keys) to a list of route handler functions (values)
        """
        r_map: Dict[str, Dict[HttpMethod, RouteHandlerFunction]] = {}
        for route in self.routes:
            if not r_map.get(route.path):
                r_map[route.path] = {}
            for method, handler in route.route_handler_map.items():
                r_map[route.path][method] = handler
        return r_map

    @staticmethod
    def create_handler_http_method_map(
        route_handler: Union[Controller, RouteHandlerFunction, "Router"],
    ) -> Dict[str, Dict[HttpMethod, RouteHandlerFunction]]:
        """
        Maps route handlers to http methods
        """
        handlers_map: Dict[str, Dict[HttpMethod, RouteHandlerFunction]] = {}
        if is_route_handler_function(route_handler):
            route_info = cast(RouteHandlerFunction, route_handler).route_info
            handlers_map[route_info.path or ""] = {
                http_method: cast(RouteHandlerFunction, route_handler)
                for http_method in cast(List[HttpMethod], as_list(route_info.http_method))
            }
        elif isinstance(route_handler, (Router, Route)):
            handlers_map = route_handler.route_handler_method_map
        else:
            # we reassign the variable to give it a clearer meaning
            controller = cast(Controller, route_handler)
            for controller_method in controller.get_route_handlers():
                path = (
                    join_paths([controller.path, controller_method.route_info.path])
                    if controller_method.route_info.path
                    else controller.path
                )
                if not handlers_map.get(path):
                    handlers_map[path] = {}
                for http_method in cast(List[HttpMethod], as_list(controller_method.route_info.http_method)):
                    handlers_map[path][http_method] = controller_method
        return handlers_map

    def register(self, route_handler: RouteHandler):
        """
        Register a Controller, Route instance or route_handler function on the router

        Accepts a subclass or instance of Controller, an instance of Router or a function/method that has been decorated
        by any of the routing decorators (e.g. route, get, post...) exported from starlite.decorators
        """
        if isclass(route_handler) and issubclass(cast(Type[Controller], route_handler), Controller):
            route_handler = cast(Type[Controller], route_handler)()
        if not (isinstance(route_handler, (Controller, Router)) or is_route_handler_function(route_handler)):
            raise ImproperlyConfiguredException(
                "Unsupported route_handler passed to Router.register. "
                "If you passed in a function or method, "
                "make sure to decorate it first with one of the routing decorators"
            )
        handlers_map = self.create_handler_http_method_map(
            route_handler=cast(Union[Controller, RouteHandlerFunction, Router], route_handler)
        )

        for route_path, method_map in handlers_map.items():
            path = join_paths([self.path, route_path])
            route_handlers = unique(method_map.values())
            if self.route_handler_method_map.get(path):
                existing_route_index = find(self.routes, "path", path)
                assert existing_route_index != -1, "unable to find existing route index"
                self.routes[existing_route_index] = Route(
                    path=path,
                    route_handlers=unique([*list(self.route_handler_method_map[path].values()), *route_handlers]),
                )
            else:
                self.routes.append(Route(path=path, route_handlers=route_handlers))

    def route(  # pylint: disable=arguments-differ
        self,
        path: str,
        http_method: Union[HttpMethod, List[HttpMethod]],
        include_in_schema: Optional[bool] = None,
        media_type: Optional[MediaType] = None,
        name: Optional[str] = None,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Union[dict, BaseModel]] = None,
        status_code: Optional[int] = None,
    ) -> Callable:
        """
        Decorator that creates a route, similarly to the route decorator exported from starlite.decorators,

        and then registers it on the given router.
        """

        def inner(function: Callable):
            route_handler = route_decorator(
                http_method=http_method,
                include_in_schema=include_in_schema,
                media_type=media_type,
                name=name,
                path=path,
                response_class=response_class,
                response_headers=response_headers,
                status_code=status_code,
            )(function)
            self.register(route_handler=cast(RouteHandlerFunction, route_handler))
            return route_handler

        return inner

    def add_route(  # pylint: disable=arguments-differ
        self,
        path: str,
        endpoint: Callable,
        http_method: Union[HttpMethod, List[HttpMethod]],
        include_in_schema: Optional[bool] = None,
        media_type: Optional[MediaType] = None,
        name: Optional[str] = None,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Union[dict, BaseModel]] = None,
        status_code: Optional[int] = None,
    ):
        """
        Creates a route handler function using router.route(**kwargs), and then registers it on the given router.
        """
        route_handler = route_decorator(
            http_method=http_method,
            include_in_schema=include_in_schema,
            media_type=media_type,
            name=name,
            path=path,
            response_class=response_class,
            response_headers=response_headers,
            status_code=status_code,
        )(endpoint)
        self.register(route_handler=cast(RouteHandlerFunction, route_handler))
