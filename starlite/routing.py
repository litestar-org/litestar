import re
from inspect import isclass
from typing import Any, Callable, Dict, List, Optional, Sequence, Union, cast

from openapi_schema_pydantic import OpenAPI
from openapi_schema_pydantic.util import construct_open_api_with_schema_class
from pydantic import validate_arguments
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route as StarletteRoute
from starlette.routing import Router as StarletteRouter
from starlette.types import ASGIApp
from typing_extensions import AsyncContextManager, Literal, Type

from starlite.controller import Controller
from starlite.enums import HttpMethod
from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers import RouteHandler
from starlite.openapi import OpenAPIConfig, create_path_item
from starlite.provide import Provide
from starlite.request import handle_request
from starlite.utils.helpers import DeprecatedProperty
from starlite.utils.sequence import find_index, unique
from starlite.utils.url import join_paths, normalize_path

param_match_regex = re.compile(r"\{(.*?)\}")


class Route(StarletteRoute):
    route_handler_map: Dict[HttpMethod, RouteHandler]

    @validate_arguments()
    def __init__(
        self,
        *,
        path: str,
        route_handlers: Union[RouteHandler, List[RouteHandler]],
    ):
        route_handlers = route_handlers if isinstance(route_handlers, list) else [route_handlers]
        self.route_handler_map = {}
        name = cast(Callable, route_handlers[0].fn).__name__
        include_in_schema = True

        for route_handler in route_handlers:
            for http_method in route_handler.http_methods:
                if self.route_handler_map.get(http_method):
                    raise ImproperlyConfiguredException(
                        f"handler already registered for path {path!r} and http method {http_method}"
                    )
                self.route_handler_map[http_method] = route_handler
                if route_handler.name:
                    name = route_handler.name
                if route_handler.include_in_schema is not None:
                    include_in_schema = route_handler.include_in_schema

        super().__init__(
            path=path,
            endpoint=self.create_endpoint_handler(self.route_handler_map),
            name=name,
            include_in_schema=include_in_schema,
            methods=[method.upper() for method in self.route_handler_map],
        )
        self.path_parameters: List[str] = param_match_regex.findall(self.path)
        for parameter in self.path_parameters:
            if ":" not in parameter or not parameter.split(":")[1]:
                raise ImproperlyConfiguredException("path parameter must declare a type: '{parameter_name:type}'")

    @staticmethod
    def create_endpoint_handler(http_handler_mapping: Dict[HttpMethod, RouteHandler]) -> Callable:
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
    owner: Optional["Router"] = None

    def __init__(
        self,
        *,
        path: str,
        route_handlers: Optional[Sequence[Union[Type[Controller], RouteHandler, "Router", Callable]]] = None,
        redirect_slashes: bool = True,
        default: Optional[ASGIApp] = None,
        on_startup: Optional[Sequence[Callable]] = None,
        on_shutdown: Optional[Sequence[Callable]] = None,
        lifespan: Optional[Callable[[Any], AsyncContextManager]] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
    ):
        if on_startup or on_shutdown:  # pragma: no cover
            assert not lifespan, "Use either 'lifespan' or 'on_startup'/'on_shutdown', not both."
        self.path = normalize_path(path)
        self.dependencies = dependencies
        super().__init__(
            default=default,
            lifespan=lifespan,
            on_shutdown=on_shutdown,
            on_startup=on_startup,
            redirect_slashes=redirect_slashes,
            routes=[],
        )
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
                controller = cast(Controller, value)
                path = join_paths([controller.path, route_handler.path]) if route_handler.path else controller.path
                if not handlers_map.get(path):
                    handlers_map[path] = {}
                for http_method in route_handler.http_methods:
                    handlers_map[path][http_method] = route_handler
        return handlers_map

    def validate_registration_value(
        self, value: Union[Type[Controller], RouteHandler, "Router", Callable]
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
        return cast(Union[Controller, RouteHandler, "Router"], value)

    def register(self, value: Union[Type[Controller], RouteHandler, "Router", Callable]):
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

    # these Starlette properties are not supported
    route = DeprecatedProperty()
    add_route = DeprecatedProperty()


class RootRouter(Router):
    owner: Literal[None] = None

    def __init__(
        self,
        *,
        openapi_config: Optional[OpenAPIConfig],
        route_handlers: Sequence[Union[Type[Controller], RouteHandler, "Router", Callable]],
        on_startup: Optional[Sequence[Callable]] = None,
        on_shutdown: Optional[Sequence[Callable]] = None,
        lifespan: Optional[Callable[[Any], AsyncContextManager]] = None,
        dependencies: Optional[Dict[str, Provide]] = None,
    ):
        self.openapi_schema = None
        self.schema_endpoint_url = None
        self.schema_response_media_type = None
        super().__init__(
            path="",
            route_handlers=route_handlers,
            on_startup=on_startup,
            on_shutdown=on_shutdown,
            lifespan=lifespan,
            dependencies=dependencies,
        )
        if openapi_config:
            self.openapi_schema = openapi_config.to_openapi_schema()
            self.schema_endpoint_url = openapi_config.schema_endpoint_url
            self.schema_response_media_type = openapi_config.schema_response_media_type
            self.update_openapi_schema_paths()
            self.routes.append(self.create_schema_endpoint())

    def register(self, value: Union[Type[Controller], RouteHandler, "Router", Callable]):
        super().register(value=value)
        if self.openapi_schema:
            self.update_openapi_schema_paths()

    def update_openapi_schema_paths(self):
        """
        Updates the OpenAPI schema with all paths registered on the root router
        """
        if not self.openapi_schema.paths:
            self.openapi_schema.paths = {}
        for route in self.routes:
            if route.include_in_schema and (route.path_format or "/") not in self.openapi_schema.paths:
                self.openapi_schema.paths[route.path_format or "/"] = create_path_item(route=route)

    # TODO: extend this to support customization, security etc.
    def create_schema_endpoint(self) -> Route:
        """Create a schema endpoint"""
        assert (
            self.schema_endpoint_url and self.schema_endpoint_url and self.schema_response_media_type
        ), "schema configuration must be set to generate a schema endpoint"

        def get_openapi_schema() -> OpenAPI:
            """handler function that returns a constructed OpenAPI model"""
            return construct_open_api_with_schema_class(self.openapi_schema)

        return Route(
            path=normalize_path(self.schema_endpoint_url),
            route_handlers=[
                RouteHandler(
                    http_method=HttpMethod.GET,
                    media_type=self.schema_response_media_type,
                    fn=get_openapi_schema,
                    include_in_schema=False,
                )
            ],
        )
