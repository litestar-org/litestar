import re
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
from traceback import format_exc
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    List,
    Set,
    Tuple,
    Type,
    Union,
    cast,
)
from uuid import UUID

from pydantic.datetime_parse import (
    parse_date,
    parse_datetime,
    parse_duration,
    parse_time,
)
from starlette.middleware import Middleware as StarletteMiddleware
from typing_extensions import TypedDict

from starlite.enums import ScopeType
from starlite.exceptions import (
    ImproperlyConfiguredException,
    MethodNotAllowedException,
    NotFoundException,
    ValidationException,
)
from starlite.utils import AsyncCallable

if TYPE_CHECKING:
    from starlite.app import Starlite
    from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute
    from starlite.routes.base import BaseRoute, PathParameterDefinition
    from starlite.types import (
        ASGIApp,
        ExceptionHandlersMap,
        LifeSpanHandler,
        LifeSpanReceive,
        LifeSpanSend,
        LifeSpanShutdownCompleteEvent,
        LifeSpanShutdownFailedEvent,
        LifeSpanStartupCompleteEvent,
        LifeSpanStartupFailedEvent,
        Receive,
        RouteHandlerType,
        Scope,
        Send,
    )


class PathParamNode:
    """Sentinel object to represent a path param in the route map."""


class PathParameterTypePathDesignator:
    """Sentinel object to a path parameter of type 'path'."""


PathParamPlaceholderType = Type[PathParamNode]
TerminusNodePlaceholderType = Type[PathParameterTypePathDesignator]
RouteMapNode = Dict[Union[str, PathParamPlaceholderType], Any]
ComponentsSet = Set[Union[str, PathParamPlaceholderType, TerminusNodePlaceholderType]]


class HandlerNode(TypedDict):
    """This class encapsulates a route handler node."""

    asgi_app: "ASGIApp"
    """ASGI App stack"""
    handler: "RouteHandlerType"
    """Route handler instance."""


def wrap_in_exception_handler(debug: bool, app: "ASGIApp", exception_handlers: "ExceptionHandlersMap") -> "ASGIApp":
    """Wraps the given ASGIApp in an instance of ExceptionHandlerMiddleware."""
    from starlite.middleware.exceptions import ExceptionHandlerMiddleware

    return ExceptionHandlerMiddleware(app=app, exception_handlers=exception_handlers, debug=debug)


def get_route_handlers(route: "BaseRoute") -> List["RouteHandlerType"]:
    """Retrieve handler(s) as a list for given route."""
    route_handlers: List["RouteHandlerType"] = []
    if hasattr(route, "route_handlers"):
        route_handlers.extend(cast("HTTPRoute", route).route_handlers)
    else:
        route_handlers.append(cast("Union[WebSocketRoute, ASGIRoute]", route).route_handler)

    return route_handlers


class ASGIRouter:
    __slots__ = (
        "app",
        "plain_routes",
        "registered_routes",
        "route_handler_index",
        "route_map",
        "route_mapping",
        "static_paths",
    )

    def __init__(
        self,
        app: "Starlite",
    ) -> None:
        """This class is the Starlite ASGI router. It handles both the ASGI
        lifespan event and routing connection requests.

        Args:
            app: The Starlite app instance
        """
        self.app = app
        self.plain_routes: Set[str] = set()
        self.registered_routes: Set["BaseRoute"] = set()
        self.route_handler_index: Dict[str, "RouteHandlerType"] = {}
        self.route_map: RouteMapNode = {}
        self.route_mapping: Dict[str, List["BaseRoute"]] = defaultdict(list)
        self.static_paths: Set[str] = set()

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """The main entry point to the Router class."""
        try:
            asgi_handlers, is_asgi = self._parse_scope_to_route(scope=scope)
            asgi_app, handler = self._resolve_handler_node(scope=scope, asgi_handlers=asgi_handlers, is_asgi=is_asgi)
        except KeyError as e:
            raise NotFoundException() from e
        scope["route_handler"] = handler
        await asgi_app(scope, receive, send)

    def _traverse_route_map(self, path: str, scope: "Scope") -> Tuple[RouteMapNode, List[str]]:
        """Traverses the application route mapping and retrieves the correct
        node for the request url.

        Args:
            path: The request's path.
            scope: The ASGI connection scope.

        Raises:
             NotFoundException: if no correlating node is found.

        Returns:
            A tuple containing the target RouteMapNode and a list containing all path parameter values.
        """
        path_params: List[str] = []
        current_node = self.route_map
        components = ["/", *[component for component in path.split("/") if component]]
        for idx, component in enumerate(components):
            components_set = cast("ComponentsSet", current_node["_components"])
            if component in components_set:
                current_node = cast("RouteMapNode", current_node[component])
                if "_static_path" in current_node:
                    self._handle_static_path(scope=scope, node=current_node)
                    break
                continue
            if PathParamNode in components_set:
                current_node = cast("RouteMapNode", current_node[PathParamNode])
                if PathParameterTypePathDesignator in components_set:
                    path_params.append("/".join(path.split("/")[idx:]))
                    break
                path_params.append(component)
                continue
            raise NotFoundException()
        return current_node, path_params

    @staticmethod
    def _handle_static_path(scope: "Scope", node: RouteMapNode) -> None:
        """Normalize the static path and update scope so file resolution will
        work as expected.

        Args:
            scope: The ASGI connection scope.
            node: Trie Node

        Returns:
            None
        """
        static_path = cast("str", node["_static_path"])
        if static_path != "/" and scope["path"].startswith(static_path):
            start_idx = len(static_path)
            scope["path"] = scope["path"][start_idx:] + "/"

    @staticmethod
    def _parse_path_parameters(
        path_parameter_definitions: List["PathParameterDefinition"], request_path_parameter_values: List[str]
    ) -> Dict[str, Any]:
        """Parses path parameters into their expected types.

        Args:
            path_parameter_definitions: A list of [PathParameterDefinition][starlite.route.base.PathParameterDefinition] instances
            request_path_parameter_values: A list of raw strings sent as path parameters as part of the request

        Raises:
            ValidationException: if path parameter parsing fails

        Returns:
            A dictionary mapping path parameter names to parsed values
        """
        result: Dict[str, Any] = {}
        parsers_map: Dict[Any, Callable] = {
            str: str,
            float: float,
            int: int,
            Decimal: Decimal,
            UUID: UUID,
            Path: lambda x: Path(re.sub("//+", "", (x.lstrip("/")))),
            date: parse_date,
            datetime: parse_datetime,
            time: parse_time,
            timedelta: parse_duration,
        }

        try:
            for idx, parameter_definition in enumerate(path_parameter_definitions):
                raw_param_value = request_path_parameter_values[idx]
                parameter_type = parameter_definition["type"]
                parameter_name = parameter_definition["name"]
                parser = parsers_map[parameter_type]
                result[parameter_name] = parser(raw_param_value)
            return result
        except (ValueError, TypeError, KeyError) as e:  # pragma: no cover
            raise ValidationException(
                f"unable to parse path parameters {','.join(request_path_parameter_values)}"
            ) from e

    def _parse_scope_to_route(self, scope: "Scope") -> Tuple[Dict[str, "HandlerNode"], bool]:
        """Given a scope object, retrieve the _asgi_handlers and _is_asgi
        values from correct trie node."""

        path = scope["path"].strip()
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        if path in self.plain_routes:
            current_node: RouteMapNode = self.route_map[path]
            path_params: List[str] = []
        else:
            current_node, path_params = self._traverse_route_map(path=path, scope=scope)

        scope["path_params"] = (
            self._parse_path_parameters(
                path_parameter_definitions=current_node["_path_parameters"], request_path_parameter_values=path_params
            )
            if path_params
            else {}
        )

        asgi_handlers = cast("Dict[str, HandlerNode]", current_node["_asgi_handlers"])
        is_asgi = cast("bool", current_node["_is_asgi"])
        return asgi_handlers, is_asgi

    @staticmethod
    def _resolve_handler_node(
        scope: "Scope", asgi_handlers: Dict[str, "HandlerNode"], is_asgi: bool
    ) -> Tuple["ASGIApp", "RouteHandlerType"]:
        """Given a scope, returns the ASGI App and route handler for the
        route."""
        if is_asgi:
            node = asgi_handlers[ScopeType.ASGI]
        elif scope["type"] == ScopeType.HTTP:
            if scope["method"] not in asgi_handlers:
                raise MethodNotAllowedException()
            node = asgi_handlers[scope["method"]]
        else:
            node = asgi_handlers[ScopeType.WEBSOCKET]
        return node["asgi_app"], node["handler"]

    async def _lifespan(self, receive: "LifeSpanReceive", send: "LifeSpanSend") -> None:
        """Handles the ASGI "lifespan" event on application startup and
        shutdown.

        Args:
            receive: The ASGI receive function.
            send: The ASGI send function.

        Returns:
            None.
        """
        message = await receive()
        try:
            shutdown_event: "LifeSpanShutdownCompleteEvent" = {"type": "lifespan.shutdown.complete"}

            if message["type"] == "lifespan.startup":
                await self.startup()
                startup_event: "LifeSpanStartupCompleteEvent" = {"type": "lifespan.startup.complete"}
                await send(startup_event)
                await receive()
            else:
                await self.shutdown()
                await send(shutdown_event)
        except BaseException as e:
            if message["type"] == "lifespan.startup":
                startup_failure_event: "LifeSpanStartupFailedEvent" = {
                    "type": "lifespan.startup.failed",
                    "message": format_exc(),
                }
                await send(startup_failure_event)
            else:
                shutdown_failure_event: "LifeSpanShutdownFailedEvent" = {
                    "type": "lifespan.shutdown.failed",
                    "message": format_exc(),
                }
                await send(shutdown_failure_event)
            raise e
        else:
            await self.shutdown()
            await send(shutdown_event)

    async def _call_lifespan_handler(self, handler: "LifeSpanHandler") -> None:
        """Determines whether the lifecycle handler expects an argument, and if
        so passes the `app.state` to it. If the handler is an async function,
        it awaits the return.

        Args:
            handler (LifeSpanHandler): sync or async callable that may or may not have an argument.
        """
        async_callable = AsyncCallable(handler)  # type: ignore

        if async_callable.num_expected_args > 0:
            await async_callable(self.app.state)  # type: ignore[arg-type]
        else:
            await async_callable()

    def _build_route_middleware_stack(
        self,
        route: Union["HTTPRoute", "WebSocketRoute", "ASGIRoute"],
        route_handler: "RouteHandlerType",
    ) -> "ASGIApp":
        """Constructs a middleware stack that serves as the point of entry for
        each route."""
        from starlite.middleware.csrf import CSRFMiddleware

        # we wrap the route.handle method in the ExceptionHandlerMiddleware
        asgi_handler = wrap_in_exception_handler(
            debug=self.app.debug, app=route.handle, exception_handlers=route_handler.resolve_exception_handlers()  # type: ignore[arg-type]
        )

        if self.app.csrf_config:
            asgi_handler = CSRFMiddleware(app=asgi_handler, config=self.app.csrf_config)

        for middleware in route_handler.resolve_middleware():
            if isinstance(middleware, StarletteMiddleware):
                handler, kwargs = middleware
                asgi_handler = handler(app=asgi_handler, **kwargs)
            else:
                asgi_handler = middleware(app=asgi_handler)  # type: ignore

        # we wrap the entire stack again in ExceptionHandlerMiddleware
        return wrap_in_exception_handler(
            debug=self.app.debug,
            app=cast("ASGIApp", asgi_handler),
            exception_handlers=route_handler.resolve_exception_handlers(),
        )  # pyright: ignore

    def _configure_route_map_node(self, route: "BaseRoute", node: RouteMapNode) -> None:
        """Set required attributes and route handlers on route_map tree
        node."""
        from starlite.routes import ASGIRoute, HTTPRoute, WebSocketRoute

        if "_path_parameters" not in node:
            node["_path_parameters"] = route.path_parameters
        if "_asgi_handlers" not in node:
            node["_asgi_handlers"] = {}
        if "_is_asgi" not in node:
            node["_is_asgi"] = False
        if route.path in self.static_paths:
            if node["_components"]:
                raise ImproperlyConfiguredException("Cannot have configured routes below a static path")
            node["_static_path"] = route.path
            node["_is_asgi"] = True
        asgi_handlers = cast("Dict[str, HandlerNode]", node["_asgi_handlers"])
        if isinstance(route, HTTPRoute):
            for method, handler_mapping in route.route_handler_map.items():
                handler, _ = handler_mapping
                asgi_handlers[method] = HandlerNode(
                    asgi_app=self._build_route_middleware_stack(route, handler),
                    handler=handler,
                )
        elif isinstance(route, WebSocketRoute):
            asgi_handlers["websocket"] = HandlerNode(
                asgi_app=self._build_route_middleware_stack(route, route.route_handler),
                handler=route.route_handler,
            )
        elif isinstance(route, ASGIRoute):
            asgi_handlers["asgi"] = HandlerNode(
                asgi_app=self._build_route_middleware_stack(route, route.route_handler),
                handler=route.route_handler,
            )
            node["_is_asgi"] = True

    def _store_handler_to_route_mapping(self, route: "BaseRoute") -> None:
        """Stores the mapping of route handlers to routes and to route handler
        names.

        Args:
            route: A Route instance.

        Returns:
            None
        """

        for handler in get_route_handlers(route):
            if handler.name in self.route_handler_index and str(self.route_handler_index[handler.name]) != str(handler):
                raise ImproperlyConfiguredException(
                    f"route handler names must be unique - {handler.name} is not unique."
                )
            identifier = handler.name or str(handler)
            self.route_mapping[identifier].append(route)
            self.route_handler_index[identifier] = handler

    def _add_node_to_route_map(self, route: "BaseRoute") -> RouteMapNode:
        """Adds a new route path (e.g. '/foo/bar/{param:int}') into the
        route_map tree.

        Inserts non-parameter paths ('plain routes') off the tree's root
        node. For paths containing parameters, splits the path on '/'
        and nests each path segment under the previous segment's node
        (see prefix tree / trie).
        """
        current_node = self.route_map
        path = route.path

        if route.path_parameters or path in self.static_paths:
            components = cast(
                "List[Union[str, PathParamPlaceholderType, PathParameterDefinition]]", ["/", *route.path_components]
            )
            for component in components:
                components_set = cast("ComponentsSet", current_node["_components"])

                if isinstance(component, dict):
                    # The rest of the path should be regarded as a parameter value.
                    if component["type"] is Path:
                        components_set.add(PathParameterTypePathDesignator)
                    # Represent path parameters using a special value
                    component = PathParamNode

                components_set.add(component)

                if component not in current_node:
                    current_node[component] = {"_components": set()}
                current_node = cast("RouteMapNode", current_node[component])
                if "_static_path" in current_node:
                    raise ImproperlyConfiguredException("Cannot have configured routes below a static path")
        else:
            if path not in self.route_map:
                self.route_map[path] = {"_components": set()}
            self.plain_routes.add(path)
            current_node = self.route_map[path]
        self._configure_route_map_node(route, current_node)
        return current_node

    def construct_route_map(self) -> None:
        """Create a map of the app's routes.

        This map is used in the asgi router to route requests.
        """
        if "_components" not in self.route_map:
            self.route_map["_components"] = set()
        new_routes = [route for route in self.app.routes if route not in self.registered_routes]
        for route in new_routes:
            node = self._add_node_to_route_map(route)
            if node["_path_parameters"] != route.path_parameters:
                raise ImproperlyConfiguredException("Should not use routes with conflicting path parameters")
            self._store_handler_to_route_mapping(route)
            self.registered_routes.add(route)

    async def startup(self) -> None:
        """Run any [LifeSpanHandlers][starlite.types.LifeSpanHandler] defined
        in the application's `.on_startup` list.

        Calls the `before_startup` hook and `after_startup` hook
        handlers respectively before and after calling in the lifespan
        handlers.
        """
        for hook in self.app.before_startup:
            await hook(self.app)

        for handler in self.app.on_startup:
            await self._call_lifespan_handler(handler)

        for hook in self.app.after_startup:
            await hook(self.app)

    async def shutdown(self) -> None:
        """Run any [LifeSpanHandlers][starlite.types.LifeSpanHandler] defined
        in the application's `.on_shutdown` list.

        Calls the `before_shutdown` hook and `after_shutdown` hook
        handlers respectively before and after calling in the lifespan
        handlers.
        """

        for hook in self.app.before_shutdown:
            await hook(self.app)

        for handler in self.app.on_shutdown:
            await self._call_lifespan_handler(handler)

        for hook in self.app.after_shutdown:
            await hook(self.app)
