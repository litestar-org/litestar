import re
from inspect import isclass
from typing import Any, Dict, List, Optional, Union, cast

from pydantic import validate_arguments
from pydantic.typing import AnyCallable
from starlette.routing import Route as StarletteRoute
from starlette.types import ASGIApp, Receive, Scope, Send
from typing_extensions import Type

from starlite.controller import Controller
from starlite.enums import HttpMethod
from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers import RouteHandler
from starlite.provide import Provide
from starlite.request import Request, handle_request
from starlite.response import Response
from starlite.types import Guard, ResponseHeader
from starlite.utils.sequence import find_index, unique
from starlite.utils.url import join_paths, normalize_path

param_match_regex = re.compile(r"{(.*?)}")


class Route(StarletteRoute):
    route_handler_map: Dict[HttpMethod, RouteHandler]

    @validate_arguments()
    def __init__(
        self,
        *,
        path: str,
        route_handlers: Union[RouteHandler, List[RouteHandler]],
    ):
        self.route_handler_map = self.parse_route_handlers(
            route_handlers=route_handlers if isinstance(route_handlers, list) else [route_handlers], path=path
        )
        # we are passing a dud lambda function as the endpoint kwarg here because we are setting self.app ourselves
        super().__init__(path=path, methods=[method.upper() for method in self.route_handler_map], endpoint=lambda x: x)
        self.app = self.create_endpoint_handler(self.route_handler_map)
        self.path_parameters: List[str] = param_match_regex.findall(self.path)
        for parameter in self.path_parameters:
            if ":" not in parameter or not parameter.split(":")[1]:
                raise ImproperlyConfiguredException("path parameter must declare a type: '{parameter_name:type}'")

    @staticmethod  #
    def parse_route_handlers(route_handlers: List[RouteHandler], path: str) -> Dict[HttpMethod, RouteHandler]:
        """
        Parses the passed in route_handlers and returns a mapping of http-methods and route handlers
        """
        mapped_route_handlers: Dict[HttpMethod, RouteHandler] = {}
        for route_handler in route_handlers:
            for http_method in route_handler.http_methods:
                if mapped_route_handlers.get(http_method):
                    raise ImproperlyConfiguredException(
                        f"handler already registered for path {path!r} and http method {http_method}"
                    )
                mapped_route_handlers[http_method] = route_handler
        return mapped_route_handlers

    @staticmethod
    def create_endpoint_handler(http_handler_mapping: Dict[HttpMethod, RouteHandler]) -> ASGIApp:
        """
        Create an ASGIApp that routes to the correct route handler based on the scope.

        Using this method, Starlite is able to support different handler functions for the same path.
        """

        async def endpoint_handler(scope: Scope, receive: Receive, send: Send) -> None:
            request: Request[Any, Any] = Request(scope, receive=receive, send=send)
            request_method = HttpMethod.from_str(request.method)
            handler = http_handler_mapping[request_method]
            response = await handle_request(route_handler=handler, request=request)
            await response(scope, receive, send)

        return endpoint_handler


# noinspection PyMethodOverriding
class Router:
    def __init__(
        self,
        *,
        path: str,
        route_handlers: List[Union[Type[Controller], RouteHandler, "Router", AnyCallable]],
        dependencies: Optional[Dict[str, Provide]] = None,
        guards: Optional[List[Guard]] = None,
        response_class: Optional[Type[Response]] = None,
        response_headers: Optional[Dict[str, ResponseHeader]] = None,
    ):
        self.owner: Optional["Router"] = None
        self.routes: List[Route] = []
        self.path = normalize_path(path)
        self.response_class = response_class
        self.dependencies = dependencies
        self.response_headers = response_headers
        self.guards = guards
        for route_handler in route_handlers or []:
            self.register(value=route_handler)

    @property
    def route_handler_method_map(self) -> Dict[str, Dict[HttpMethod, RouteHandler]]:
        """
        Returns dictionary that maps paths (keys) to a list of route handler functions (values)
        """
        r_map: Dict[str, Dict[HttpMethod, RouteHandler]] = {}
        for r in self.routes:
            if not r_map.get(r.path):
                r_map[r.path] = {}
            for method, handler in r.route_handler_map.items():
                r_map[r.path][method] = handler
        return r_map

    @staticmethod
    def create_handler_http_method_map(
        value: Union[Controller, RouteHandler, "Router"],
    ) -> Dict[str, Dict[HttpMethod, RouteHandler]]:
        """
        Maps route handlers to http methods
        """
        handlers_map: Dict[str, Dict[HttpMethod, RouteHandler]] = {}
        if isinstance(value, RouteHandler):
            handlers_map[value.path or ""] = {http_method: value for http_method in value.http_methods}
        elif isinstance(value, Router):
            handlers_map = value.route_handler_method_map
        else:
            # we reassign the variable to give it a clearer meaning
            for route_handler in value.get_route_handlers():
                path = join_paths([value.path, route_handler.path]) if route_handler.path else value.path
                if not handlers_map.get(path):
                    handlers_map[path] = {}
                for http_method in route_handler.http_methods:
                    handlers_map[path][http_method] = route_handler
        return handlers_map

    def validate_registration_value(
        self, value: Union[Type[Controller], RouteHandler, "Router", AnyCallable]
    ) -> Union[Controller, RouteHandler, "Router"]:
        """
        Validates that the value passed to the register method is supported
        """
        if isclass(value) and issubclass(cast(Type[Controller], value), Controller):
            return cast(Type[Controller], value)(owner=self)
        if not isinstance(value, (Router, RouteHandler)):
            raise ImproperlyConfiguredException(
                "Unsupported value passed to `Router.register`. "
                "If you passed in a function or method, "
                "make sure to decorate it first with one of the routing decorators"
            )
        if isinstance(value, Router):
            if value.owner:
                raise ImproperlyConfiguredException(f"Router with path {value.path} has already been registered")
            if value is self:
                raise ImproperlyConfiguredException("Cannot register a router on itself")
            if not value.owner:
                value.owner = self
        else:
            # the route handler is copied to ensure each time the route handler is registerd,
            # we get an instance with a unique owner
            value = value.copy()
            value.owner = self
        return cast(Union[Controller, RouteHandler, "Router"], value)

    def register(self, value: Union[Type[Controller], RouteHandler, "Router", AnyCallable]) -> None:
        """
        Register a Controller, Route instance or RouteHandler on the router

        Accepts a subclass or instance of Controller, an instance of Router or a function/method that has been decorated
        by any of the routing decorators (e.g. route, get, post...) exported from 'starlite.routing'
        """
        validated_value = self.validate_registration_value(value)
        if not validated_value.owner:
            validated_value.owner = self
        handlers_map = self.create_handler_http_method_map(value=validated_value)

        for route_path, method_map in handlers_map.items():
            path = join_paths([self.path, route_path])
            route_handlers = unique(method_map.values())
            if self.route_handler_method_map.get(path):
                existing_route_index = find_index(
                    self.routes, lambda x: x.path == path  # pylint: disable=cell-var-from-loop
                )
                assert existing_route_index != -1, "unable to find_index existing route index"
                self.routes[existing_route_index] = Route(
                    path=path,
                    route_handlers=unique([*list(self.route_handler_method_map[path].values()), *route_handlers]),
                )
            else:
                self.routes.append(Route(path=path, route_handlers=route_handlers))
