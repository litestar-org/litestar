from inspect import getfullargspec, isawaitable, ismethod
from typing import TYPE_CHECKING, Any, Dict, List, Set, Tuple, Type, Union, cast

from starlette.routing import Router as StarletteRouter

from starlite.enums import ScopeType
from starlite.exceptions import (
    MethodNotAllowedException,
    NotFoundException,
    ValidationException,
)

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send

    from starlite.app import Starlite
    from starlite.routes.base import PathParameterDefinition
    from starlite.types import LifeCycleHandler


class PathParamPlaceholder:
    """Sentinel object to represent a path param in the route map."""


PathParamPlaceholderType = Type[PathParamPlaceholder]
RouteMapNode = Dict[Union[str, PathParamPlaceholderType], Any]
ComponentsSet = Set[Union[str, PathParamPlaceholderType]]


class StarliteASGIRouter(StarletteRouter):
    """This class extends the Starlette Router class and *is* the ASGI app used
    in Starlite."""

    def __init__(
        self,
        app: "Starlite",
        on_shutdown: List["LifeCycleHandler"],
        on_startup: List["LifeCycleHandler"],
    ):
        self.app = app
        super().__init__(on_startup=on_startup, on_shutdown=on_shutdown)

    def _traverse_route_map(self, path: str, scope: "Scope") -> Tuple[RouteMapNode, List[str]]:
        """Traverses the application route mapping and retrieves the correct
        node for the request url.

        Raises NotFoundException if no correlating node is found
        """
        path_params: List[str] = []
        current_node = self.app.route_map
        components = ["/", *[component for component in path.split("/") if component]]
        for component in components:
            components_set = cast("ComponentsSet", current_node["_components"])
            if component in components_set:
                current_node = cast("RouteMapNode", current_node[component])
                if "_static_path" in current_node:
                    self._handle_static_path(scope=scope, node=current_node)
                    break
                continue
            if PathParamPlaceholder in components_set:
                path_params.append(component)
                current_node = cast("RouteMapNode", current_node[PathParamPlaceholder])
                continue
            raise NotFoundException()
        return current_node, path_params

    @staticmethod
    def _handle_static_path(scope: "Scope", node: RouteMapNode) -> None:
        """Normalize the static path and update scope so file resolution will
        work as expected.

        Args:
            scope: Request Scope
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
            ValidationException

        Returns:
            A dictionary mapping path parameter names to parsed values
        """
        result: Dict[str, Any] = {}

        try:
            for idx, parameter_definition in enumerate(path_parameter_definitions):
                raw_param_value = request_path_parameter_values[idx]
                parameter_type = parameter_definition["type"]
                parameter_name = parameter_definition["name"]
                result[parameter_name] = parameter_type(raw_param_value)
            return result
        except (ValueError, TypeError, KeyError) as e:  # pragma: no cover
            raise ValidationException(
                f"unable to parse path parameters {','.join(request_path_parameter_values)}"
            ) from e

    def _parse_scope_to_route(self, scope: "Scope") -> Tuple[Dict[str, "ASGIApp"], bool]:
        """Given a scope object, retrieve the _asgi_handlers and _is_asgi
        values from correct trie node."""

        path = cast("str", scope["path"]).strip()
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

        asgi_handlers = cast("Dict[str, ASGIApp]", current_node["_asgi_handlers"])
        is_asgi = cast("bool", current_node["_is_asgi"])
        return asgi_handlers, is_asgi

    @staticmethod
    def _resolve_asgi_app(scope: "Scope", asgi_handlers: Dict[str, "ASGIApp"], is_asgi: bool) -> "ASGIApp":
        """Given a scope, retrieves the correct ASGI App for the route."""
        if is_asgi:
            return asgi_handlers[ScopeType.ASGI]
        if scope["type"] == ScopeType.HTTP:
            if scope["method"] not in asgi_handlers:
                raise MethodNotAllowedException()
            return asgi_handlers[scope["method"]]
        return asgi_handlers[ScopeType.WEBSOCKET]

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """The main entry point to the Router class."""
        try:
            asgi_handlers, is_asgi = self._parse_scope_to_route(scope=scope)
            asgi_handler = self._resolve_asgi_app(scope=scope, asgi_handlers=asgi_handlers, is_asgi=is_asgi)
        except KeyError as e:
            raise NotFoundException() from e
        await asgi_handler(scope, receive, send)

    async def _call_lifecycle_handler(self, handler: "LifeCycleHandler") -> None:
        """Determines whether the lifecycle handler expects an argument, and if
        so passes the `app.state` to it. If the handler is an async function,
        it awaits the return.

        Args:
            handler (LifeCycleHandler): sync or async callable that may or may not have an argument.
        """
        arg_spec = getfullargspec(handler)
        if (not ismethod(handler) and len(arg_spec.args) == 1) or (ismethod(handler) and len(arg_spec.args) == 2):
            value = handler(self.app.state)  # type:ignore[call-arg]
        else:
            value = handler()  # type:ignore[call-arg]
        if isawaitable(value):
            await value

    async def startup(self) -> None:
        """Run any `.on_startup` event handlers."""
        for handler in self.on_startup:
            await self._call_lifecycle_handler(handler)

    async def shutdown(self) -> None:
        """Run any `.on_shutdown` event handlers."""
        for handler in self.on_shutdown:
            await self._call_lifecycle_handler(handler)
