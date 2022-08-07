from inspect import getfullargspec, isawaitable, ismethod
from typing import TYPE_CHECKING, Any, Dict, List, Tuple, cast

from starlette.routing import Router as StarletteRouter
from starlette.types import ASGIApp, Receive, Scope, Send

from starlite.enums import ScopeType
from starlite.exceptions import MethodNotAllowedException, NotFoundException
from starlite.parsers import parse_path_params

if TYPE_CHECKING:
    from typing import Set

    from starlite.app import Starlite
    from starlite.types import LifeCycleHandler


class StarliteASGIRouter(StarletteRouter):
    """
    This class extends the Starlette Router class and *is* the ASGI app used in Starlite
    """

    def __init__(
        self,
        app: "Starlite",
        on_shutdown: List["LifeCycleHandler"],
        on_startup: List["LifeCycleHandler"],
    ):
        self.app = app
        super().__init__(on_startup=on_startup, on_shutdown=on_shutdown)

    def traverse_route_map(self, path: str, scope: Scope) -> Tuple[Dict[str, Any], List[str]]:
        """
        Traverses the application route mapping and retrieves the correct node for the request url.

        Raises NotFoundException if no correlating node is found
        """
        path_params: List[str] = []
        cur = self.app.route_map
        components = ["/", *[component for component in path.split("/") if component]]
        for component in components:
            components_set = cast("Set[str]", cur["_components"])
            if component in components_set:
                cur = cast("Dict[str, Any]", cur[component])
                continue
            if "*" in components_set:
                path_params.append(component)
                cur = cast("Dict[str, Any]", cur["*"])
                continue
            if cur.get("static_path"):
                static_path = cast("str", cur["static_path"])
                if static_path != "/" and scope["path"].startswith(static_path):
                    start_idx = len(static_path)
                    scope["path"] = scope["path"][start_idx:]
                break
            raise NotFoundException()
        return cur, path_params

    def parse_scope_to_route(self, scope: Scope) -> Tuple[Dict[str, ASGIApp], bool]:
        """
        Given a scope object, retrieve the _asgi_handlers and _is_asgi values from correct trie node.
        """

        path = cast("str", scope["path"]).strip()
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        if path in self.app.plain_routes:
            cur: Dict[str, Any] = self.app.route_map[path]
            path_params: List[str] = []
        else:
            cur, path_params = self.traverse_route_map(path=path, scope=scope)
        scope["path_params"] = (
            parse_path_params(cur["_path_parameters"], path_params) if cur["_path_parameters"] else {}
        )
        asgi_handlers = cast("Dict[str, ASGIApp]", cur["_asgi_handlers"])
        is_asgi = cast("bool", cur["_is_asgi"])
        return asgi_handlers, is_asgi

    @staticmethod
    def resolve_asgi_app(scope: Scope, asgi_handlers: Dict[str, ASGIApp], is_asgi: bool) -> ASGIApp:
        """
        Given a scope, retrieves the correct ASGI App for the route
        """
        if is_asgi:
            return asgi_handlers[ScopeType.ASGI]
        if scope["type"] == ScopeType.HTTP:
            if scope["method"] not in asgi_handlers:
                raise MethodNotAllowedException()
            return asgi_handlers[scope["method"]]
        return asgi_handlers[ScopeType.WEBSOCKET]

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The main entry point to the Router class.
        """
        try:
            asgi_handlers, is_asgi = self.parse_scope_to_route(scope=scope)
            asgi_handler = self.resolve_asgi_app(scope=scope, asgi_handlers=asgi_handlers, is_asgi=is_asgi)
        except KeyError as e:
            raise NotFoundException() from e
        await asgi_handler(scope, receive, send)

    async def call_lifecycle_handler(self, handler: "LifeCycleHandler") -> None:
        """
        Determines whether the lifecycle handler expects an argument, and if so passed the app.state to it.
        If the handler is an async function, it awaits the return.
        """
        arg_spec = getfullargspec(handler)
        if (not ismethod(handler) and len(arg_spec.args) == 1) or (ismethod(handler) and len(arg_spec.args) == 2):
            value = handler(self.app.state)  # type: ignore
        else:
            value = handler()  # type: ignore
        if isawaitable(value):
            await value

    async def startup(self) -> None:
        """
        Run any `.on_startup` event handlers.
        """
        for handler in self.on_startup:
            await self.call_lifecycle_handler(handler)

    async def shutdown(self) -> None:
        """
        Run any `.on_shutdown` event handlers.
        """
        for handler in self.on_shutdown:
            await self.call_lifecycle_handler(handler)
