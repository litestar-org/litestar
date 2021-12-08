from inspect import isclass, isfunction, ismethod
from typing import Any, Callable, List, Optional, Sequence, Union, cast

from pydantic import BaseModel
from starlette.responses import Response
from starlette.routing import BaseRoute, Route
from starlette.routing import Router as StarletteRouter
from starlette.types import ASGIApp
from typing_extensions import AsyncContextManager, Type

from starlite.controller import Controller
from starlite.decorators import route as route_decorator
from starlite.enums import HttpMethod, MediaType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.types import RouteHandler
from starlite.utils.sequence import as_iterable
from starlite.utils.url import join_paths, normalize_path


# noinspection PyMethodOverriding
class Router(StarletteRouter):
    def __init__(
        self,
        path: str,
        routes: Optional[Sequence[Union[Controller, RouteHandler, BaseRoute]]] = None,
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
        for route_handler in routes or []:
            self.register(route_handler=route_handler)

    def register(self, route_handler: Union[Type[Controller], Controller, "Router", RouteHandler]):
        """
        Register a Controller, Route instance or route_handler function on the router

        Accepts a subclass of Controller, an instance of Route or a function/method that has been decorated
        by any of the routing decorators (e.g. route, get, post...) exported from starlite.decorators
        """
        routes = []
        if isinstance(route_handler, (Router, Controller)):
            routes.extend(route_handler.routes)
        elif isclass(route_handler) and issubclass(cast(Type[Controller], route_handler), Controller):
            instance = route_handler()
            routes.extend(instance.routes)
        elif (ismethod(route_handler) or isfunction(route_handler)) and hasattr(  # noqa: SIM106
            cast(Callable, route_handler), "route_info"
        ):
            route_info = cast(RouteHandler, route_handler).route_info
            routes.append(
                Route(
                    endpoint=route_handler,
                    include_in_schema=route_info.include_in_schema,
                    methods=[method.upper() for method in as_iterable(route_info.http_method)],
                    name=route_info.name,
                    path=route_info.path,
                )
            )
        else:
            raise ImproperlyConfiguredException(
                "Unsupported route_handler passed to Router.register. "
                "If you passed in a function or method, "
                "make sure to decorate it first with one of the routing decorators"
            )
        for route in routes:
            self.routes.append(
                Route(
                    endpoint=route.endpoint,
                    include_in_schema=route.include_in_schema,
                    methods=route.methods,
                    name=route.name,
                    path=join_paths([self.path, route.path]),
                )
            )

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
            self.register(route_handler=cast(RouteHandler, route_handler))
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
        self.register(route_handler=cast(RouteHandler, route_handler))
