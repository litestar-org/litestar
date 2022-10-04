import re
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from pathlib import Path
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
from starlette.routing import Router as StarletteRouter

from starlite.enums import ScopeType
from starlite.exceptions import (
    MethodNotAllowedException,
    NotFoundException,
    ValidationException,
)
from starlite.utils import AsyncCallable

if TYPE_CHECKING:
    from starlite.app import HandlerNode, Starlite
    from starlite.routes.base import PathParameterDefinition
    from starlite.types import (
        ASGIApp,
        LifeSpanHandler,
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


class StarliteASGIRouter(StarletteRouter):
    """This class extends the Starlette Router class and *is* the ASGI app used
    in Starlite."""

    def __init__(
        self,
        app: "Starlite",
        on_shutdown: List["LifeSpanHandler"],
        on_startup: List["LifeSpanHandler"],
    ) -> None:
        self.app = app
        super().__init__(on_startup=on_startup, on_shutdown=on_shutdown)

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
        current_node = self.app.route_map
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
        if path in self.app.plain_routes:
            current_node: RouteMapNode = self.app.route_map[path]
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

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:  # type: ignore[override]
        """The main entry point to the Router class."""
        try:
            asgi_handlers, is_asgi = self._parse_scope_to_route(scope=scope)
            asgi_app, handler = self._resolve_handler_node(scope=scope, asgi_handlers=asgi_handlers, is_asgi=is_asgi)
        except KeyError as e:
            raise NotFoundException() from e
        scope["route_handler"] = handler
        await asgi_app(scope, receive, send)

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

    async def startup(self) -> None:
        """Run any [LifeSpanHandlers][starlite.types.LifeSpanHandler] defined
        in the application's `.on_startup` list.

        Calls the `before_startup` hook and `after_startup` hook
        handlers respectively before and after calling in the lifespan
        handlers.
        """
        for hook in self.app.before_startup:
            await hook(self.app)

        for handler in self.on_startup:
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

        for handler in self.on_shutdown:
            await self._call_lifespan_handler(handler)

        for hook in self.app.after_shutdown:
            await hook(self.app)
