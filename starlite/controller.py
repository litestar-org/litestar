from functools import cached_property
from typing import Callable, Dict, List, Optional, Tuple, cast

from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from starlite.decorators import RouteInfo
from starlite.enums import HttpMethod
from starlite.exceptions import ConfigurationException
from starlite.types import RouteHandler
from starlite.utils.endpoint import handle_request
from starlite.utils.http_handler import is_http_handler


def create_endpoint_handler(http_handler_mapping: Dict[HttpMethod, RouteHandler]) -> Callable:
    """
    Helper to create an endpoint handler given a dictionary mapping http-methods to callables

    """

    async def inner(request: Request) -> Response:
        request_method = cast(HttpMethod, request.method.lower())
        handler = http_handler_mapping[request_method]
        return await handle_request(route_handler=handler, request=request)

    return inner


class Controller:
    dependencies: Optional[Dict[str, Callable]]

    @cached_property
    def route_handlers(self) -> Dict[str, List[Tuple[RouteHandler, RouteInfo]]]:
        """
        Returns dictionary that maps urls (keys) to a list of methods (values)
        """
        route_handlers: List[RouteHandler] = [
            getattr(self, f_name)
            for f_name in dir(self)
            if f_name not in dir(Controller) and is_http_handler(getattr(self, f_name))
        ]

        url_route_handler_map: Dict[str, List[Tuple[RouteHandler, RouteInfo]]] = {}

        for route_handler in route_handlers:
            assert route_handler.route_info, "missing route_info data"
            url = route_handler.route_info.url or "/"
            if not url_route_handler_map.get(url):
                url_route_handler_map[url] = []
            url_route_handler_map[url].append((route_handler, route_handler.route_info))

        return url_route_handler_map

    @cached_property
    def routes(self) -> List[Route]:
        """Maps http handler method defined on the class into a list of Starlette Route instances"""
        routes = []
        for url, method_group in self.route_handlers.items():
            method_map: Dict[HttpMethod, RouteHandler] = {}
            endpoint_name = None
            include_in_schema = True
            for method, route_info in method_group:
                if method_map.get(route_info.http_method):
                    raise ConfigurationException(
                        f"handler already registered for url {url} and http method {route_info.http_method}"
                    )
                method_map[route_info.http_method] = method
                if not endpoint_name and route_info.name:
                    endpoint_name = route_info.name
                if route_info.include_in_schema is False:
                    include_in_schema = False

            routes.append(
                Route(
                    path=url,
                    endpoint=create_endpoint_handler(method_map),
                    methods=list(map(lambda x: x.upper(), method_map.keys())),
                    include_in_schema=include_in_schema,
                    name=endpoint_name,
                )
            )
        return routes
