import pickle
from functools import partial
from itertools import chain
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast

from anyio.to_thread import run_sync
from starlette.responses import RedirectResponse
from starlette.routing import get_name

from starlite.connection import Request
from starlite.controller import Controller
from starlite.enums import ScopeType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.routes.base import BaseRoute
from starlite.signature import get_signature_model
from starlite.utils import is_async_callable

if TYPE_CHECKING:
    from starlette.responses import Response as StarletteResponse

    from starlite.handlers.http import HTTPRouteHandler
    from starlite.kwargs import KwargsModel
    from starlite.response import Response
    from starlite.types import AnyCallable, HTTPScope, Method, Receive, Scope, Send


class HTTPRoute(BaseRoute):
    __slots__ = (
        "route_handler_map",
        "route_handlers",
    )

    def __init__(
        self,
        *,
        path: str,
        route_handlers: List["HTTPRouteHandler"],
    ) -> None:
        """This class handles a multiple HTTP Routes.

        Args:
            path: The path for the route.
            route_handlers: A list of [HTTPRouteHandler][starlite.handlers.http.HTTPRouteHandler].
        """
        self.route_handlers = route_handlers
        self.route_handler_map: Dict["Method", Tuple["HTTPRouteHandler", "KwargsModel"]] = {}
        super().__init__(
            methods=list(chain.from_iterable([route_handler.http_methods for route_handler in route_handlers])),
            path=path,
            scope_type=ScopeType.HTTP,
            handler_names=[get_name(cast("AnyCallable", route_handler.fn)) for route_handler in route_handlers],
        )

    async def handle(self, scope: "HTTPScope", receive: "Receive", send: "Send") -> None:  # type: ignore[override]
        """ASGI app that creates a Request from the passed in args, determines
        which handler function to call and then handles the call.

        Args:
            scope: The ASGI connection scope.
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None
        """
        request: "Request[Any, Any]" = scope["app"].request_class(scope=scope, receive=receive, send=send)
        route_handler, parameter_model = self.route_handler_map[scope["method"]]

        if route_handler.resolve_guards():
            await route_handler.authorize_connection(connection=request)

        response = await self._get_response_for_request(
            scope=scope, request=request, route_handler=route_handler, parameter_model=parameter_model
        )

        await response(scope, receive, send)  # type: ignore[arg-type]
        after_response_handler = route_handler.resolve_after_response()
        if after_response_handler:
            await after_response_handler(request)  # type: ignore

    def create_handler_map(self) -> None:
        """Parses the passed in route_handlers and returns a mapping of http-
        methods and route handlers."""
        for route_handler in self.route_handlers:
            kwargs_model = self.create_handler_kwargs_model(route_handler=route_handler)
            for http_method in route_handler.http_methods:
                if self.route_handler_map.get(http_method):
                    raise ImproperlyConfiguredException(
                        f"Handler already registered for path {self.path!r} and http method {http_method}"
                    )
                self.route_handler_map[http_method] = (route_handler, kwargs_model)

    async def _get_response_for_request(
        self,
        scope: "Scope",
        request: Request[Any, Any],
        route_handler: "HTTPRouteHandler",
        parameter_model: "KwargsModel",
    ) -> "StarletteResponse":
        """Handles creating a response instance and/or using cache.

        Args:
            scope: The Request's scope
            request: The Request instance
            route_handler: The HTTPRouteHandler instance
            parameter_model: The Handler's KwargsModel

        Returns:
            An instance of StarletteResponse or a subclass of it
        """
        response: Optional["StarletteResponse"] = None
        if route_handler.cache:
            response = await self._get_cached_response(request=request, route_handler=route_handler)

        if not response:
            response = await self._call_handler_function(
                scope=scope, request=request, parameter_model=parameter_model, route_handler=route_handler
            )
            if route_handler.cache:
                await self._set_cached_response(
                    response=response,
                    request=request,
                    route_handler=route_handler,
                )

        return response

    async def _call_handler_function(
        self, scope: "Scope", request: Request, parameter_model: "KwargsModel", route_handler: "HTTPRouteHandler"
    ) -> "StarletteResponse":
        """Calls the before request handlers, retrieves any data required for
        the route handler, and calls the route handler's to_response method.

        This is wrapped in a try except block - and if an exception is raised,
        it tries to pass it to an appropriate exception handler - if defined.
        """
        response_data = None
        before_request_handler = route_handler.resolve_before_request()

        if before_request_handler:
            response_data = await before_request_handler(request)

        if not response_data:
            response_data = await self._get_response_data(
                route_handler=route_handler, parameter_model=parameter_model, request=request
            )

        if isinstance(response_data, RedirectResponse):
            return response_data

        return await route_handler.to_response(
            app=scope["app"],
            data=response_data,
            plugins=request.app.plugins,
            request=request,
        )

    @staticmethod
    async def _get_response_data(
        route_handler: "HTTPRouteHandler", parameter_model: "KwargsModel", request: Request
    ) -> Any:
        """Determines what kwargs are required for the given route handler's
        'fn' and calls it."""
        signature_model = get_signature_model(route_handler)
        if parameter_model.has_kwargs:
            kwargs = parameter_model.to_kwargs(connection=request)
            request_data = kwargs.get("data")
            if request_data:
                kwargs["data"] = await request_data
            for dependency in parameter_model.expected_dependencies:
                kwargs[dependency.key] = await parameter_model.resolve_dependency(
                    dependency=dependency, connection=request, **kwargs
                )
            parsed_kwargs = signature_model.parse_values_from_connection_kwargs(connection=request, **kwargs)
        else:
            parsed_kwargs = {}
        if isinstance(route_handler.owner, Controller):
            fn = partial(cast("AnyCallable", route_handler.fn), route_handler.owner, **parsed_kwargs)
        else:
            fn = partial(cast("AnyCallable", route_handler.fn), **parsed_kwargs)
        if is_async_callable(fn):
            return await fn()
        if route_handler.sync_to_thread:
            return await run_sync(fn)
        return fn()

    @staticmethod
    async def _get_cached_response(
        request: Request, route_handler: "HTTPRouteHandler"
    ) -> Optional["StarletteResponse"]:
        """Retrieves and un-pickles the cached response, if existing.

        Args:
            request: The [Request][starlite.connection.Request] instance
            route_handler: The [HTTPRouteHandler][starlite.handlers.http.HTTPRouteHandler] instance

        Returns:
            A cached response instance, if existing.
        """

        cache = request.app.cache
        cache_key = cache.build_cache_key(request=request, cache_key_builder=route_handler.cache_key_builder)
        cached_response = await cache.get(key=cache_key)

        if cached_response:
            return cast("StarletteResponse", pickle.loads(cached_response))  # nosec

        return None

    @staticmethod
    async def _set_cached_response(
        response: Union["Response", "StarletteResponse"], request: Request, route_handler: "HTTPRouteHandler"
    ) -> None:
        """Pickles and caches a response object."""
        cache = request.app.cache
        cache_key = cache.build_cache_key(request, route_handler.cache_key_builder)

        await cache.set(
            key=cache_key,
            value=pickle.dumps(response, pickle.HIGHEST_PROTOCOL),
            expiration=route_handler.cache if isinstance(route_handler.cache, int) else None,
        )
