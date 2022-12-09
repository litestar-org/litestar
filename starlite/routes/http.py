import pickle
from itertools import chain
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union, cast

from starlite.connection import Request
from starlite.constants import DEFAULT_ALLOWED_CORS_HEADERS
from starlite.datastructures.headers import Headers
from starlite.datastructures.upload_file import UploadFile
from starlite.enums import HttpMethod, MediaType, ScopeType
from starlite.exceptions import ImproperlyConfiguredException
from starlite.handlers.http import HTTPRouteHandler
from starlite.response import Response
from starlite.routes.base import BaseRoute
from starlite.status_codes import HTTP_204_NO_CONTENT, HTTP_400_BAD_REQUEST

if TYPE_CHECKING:
    from starlite.datastructures.provide import DependencyCleanupGroup
    from starlite.kwargs import KwargsModel
    from starlite.types import ASGIApp, HTTPScope, Method, Receive, Scope, Send


class HTTPRoute(BaseRoute):
    """An HTTP route, capable of handling multiple `HTTPRouteHandler`s."""

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
        """Initialize `HTTPRoute`.

        Args:
            path: The path for the route.
            route_handlers: A list of [HTTPRouteHandler][starlite.handlers.http.HTTPRouteHandler].
        """
        methods = list(chain.from_iterable([route_handler.http_methods for route_handler in route_handlers]))
        if "OPTIONS" not in methods:
            methods.append("OPTIONS")
            route_handlers.append(self.create_options_handler(path))

        self.route_handlers = route_handlers
        self.route_handler_map: Dict["Method", Tuple["HTTPRouteHandler", "KwargsModel"]] = {}

        super().__init__(
            methods=methods,
            path=path,
            scope_type=ScopeType.HTTP,
            handler_names=[route_handler.handler_name for route_handler in self.route_handlers],
        )

    async def handle(self, scope: "HTTPScope", receive: "Receive", send: "Send") -> None:  # type: ignore[override]
        """ASGI app that creates a Request from the passed in args, determines which handler function to call and then
        handles the call.

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

        await response(scope, receive, send)

        if after_response_handler := route_handler.resolve_after_response():
            await after_response_handler(request)  # type: ignore

        if form_data := scope.get("_form", {}):
            await self._cleanup_temporary_files(form_data=cast("Dict[str, Any]", form_data))

    def create_handler_map(self) -> None:
        """Parse the `router_handlers` of this route and return a mapping of
        http- methods and route handlers.
        """
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
    ) -> "ASGIApp":
        """Return a response for the request.

        If caching is enabled and a response exist in the cache, the cached response will be returned.
        If caching is enabled and a response does not exist in the cache, the newly created
        response will be cached.

        Args:
            scope: The Request's scope
            request: The Request instance
            route_handler: The HTTPRouteHandler instance
            parameter_model: The Handler's KwargsModel

        Returns:
            An instance of Response or a compatible ASGIApp or a subclass of it
        """
        if route_handler.cache and (
            response := await self._get_cached_response(request=request, route_handler=route_handler)
        ):
            return response

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
    ) -> "ASGIApp":
        """Call the before request handlers, retrieve any data required for the route handler, and call the route
        handler's `to_response` method.

        This is wrapped in a try except block - and if an exception is raised,
        it tries to pass it to an appropriate exception handler - if defined.
        """
        response_data: Any = None
        cleanup_group: Optional["DependencyCleanupGroup"] = None

        if before_request_handler := route_handler.resolve_before_request():
            response_data = await before_request_handler(request)

        if not response_data:
            response_data, cleanup_group = await self._get_response_data(
                route_handler=route_handler, parameter_model=parameter_model, request=request
            )

        response: "ASGIApp" = (
            response_data  # type: ignore[assignment]
            if isinstance(response_data, Response)
            else await route_handler.to_response(
                app=scope["app"],
                data=response_data,
                plugins=request.app.plugins,
                request=request,
            )
        )

        if cleanup_group:
            await cleanup_group.cleanup()

        return response

    @staticmethod
    async def _get_response_data(
        route_handler: "HTTPRouteHandler", parameter_model: "KwargsModel", request: Request
    ) -> Tuple[Any, Optional["DependencyCleanupGroup"]]:
        """Determine what kwargs are required for the given route handler's `fn` and calls it."""
        parsed_kwargs: Dict[str, Any] = {}
        cleanup_group: Optional["DependencyCleanupGroup"] = None

        if parameter_model.has_kwargs and route_handler.signature_model:
            kwargs = parameter_model.to_kwargs(connection=request)

            if "data" in kwargs:
                kwargs["data"] = await kwargs["data"]

            if parameter_model.dependency_batches:
                cleanup_group = await parameter_model.resolve_dependencies(request, kwargs)

            parsed_kwargs = route_handler.signature_model.parse_values_from_connection_kwargs(
                connection=request, **kwargs
            )

        if cleanup_group:
            async with cleanup_group:
                if route_handler.has_sync_callable:
                    data = route_handler.fn.value(**parsed_kwargs)
                else:
                    data = await route_handler.fn.value(**parsed_kwargs)

        else:
            if route_handler.has_sync_callable:
                data = route_handler.fn.value(**parsed_kwargs)
            else:
                data = await route_handler.fn.value(**parsed_kwargs)

        return data, cleanup_group

    @staticmethod
    async def _get_cached_response(request: Request, route_handler: "HTTPRouteHandler") -> Optional["ASGIApp"]:
        """Retrieve and un-pickle the cached response, if existing.

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
            return cast("ASGIApp", pickle.loads(cached_response))  # nosec # noqa: SCS113

        return None

    @staticmethod
    async def _set_cached_response(
        response: Union["Response", "ASGIApp"], request: Request, route_handler: "HTTPRouteHandler"
    ) -> None:
        """Pickles and caches a response object."""
        cache = request.app.cache
        cache_key = cache.build_cache_key(request, route_handler.cache_key_builder)

        await cache.set(
            key=cache_key,
            value=pickle.dumps(response, pickle.HIGHEST_PROTOCOL),
            expiration=route_handler.cache if isinstance(route_handler.cache, int) else None,
        )

    def create_options_handler(self, path: str) -> "HTTPRouteHandler":
        """

        Args:
            path: The route path

        Returns:
            An HTTP route handler for OPTIONS requests.
        """

        def options_handler(scope: "Scope") -> Response:
            """
            Handler function for OPTIONS requests.
            Args:
                scope: The ASGI Scope.

            Returns:
                Response
            """
            cors_config = scope["app"].cors_config
            request_headers = Headers.from_scope(scope=scope)
            origin = request_headers.get("origin")

            if cors_config and origin:
                pre_flight_method = request_headers.get("Access-Control-Request-Method")
                failures = []

                if not cors_config.is_allow_all_methods and (
                    pre_flight_method and pre_flight_method not in cors_config.allow_methods
                ):
                    failures.append("method")

                response_headers = cors_config.preflight_headers.copy()

                if not cors_config.is_origin_allowed(origin):
                    failures.append("Origin")
                elif response_headers.get("Access-Control-Allow-Origin") != "*":
                    response_headers["Access-Control-Allow-Origin"] = origin

                pre_flight_requested_headers = [
                    header.strip()
                    for header in request_headers.get("Access-Control-Request-Headers", "").split(",")
                    if header.strip()
                ]

                if pre_flight_requested_headers:
                    if cors_config.is_allow_all_headers:
                        response_headers["Access-Control-Allow-Headers"] = ", ".join(
                            sorted(set(pre_flight_requested_headers) | DEFAULT_ALLOWED_CORS_HEADERS)
                        )
                    elif any(
                        header.lower() not in cors_config.allow_headers for header in pre_flight_requested_headers
                    ):
                        failures.append("headers")

                return (
                    Response(
                        content=f"Disallowed CORS {', '.join(failures)}",
                        status_code=HTTP_400_BAD_REQUEST,
                        media_type=MediaType.TEXT,
                    )
                    if failures
                    else Response(
                        content=None,
                        status_code=HTTP_204_NO_CONTENT,
                        media_type=MediaType.TEXT,
                        headers=response_headers,
                    )
                )

            return Response(
                content=None,
                status_code=HTTP_204_NO_CONTENT,
                headers={"Allow": ", ".join(sorted(self.methods))},
                media_type=MediaType.TEXT,
            )

        return HTTPRouteHandler(
            path=path,
            http_method=[HttpMethod.OPTIONS],
            include_in_schema=False,
        )(options_handler)

    @staticmethod
    async def _cleanup_temporary_files(form_data: Dict[str, Any]) -> None:
        for v in form_data.values():
            if isinstance(v, UploadFile) and not v.file.closed:
                await v.close()
