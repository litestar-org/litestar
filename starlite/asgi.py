from inspect import getfullargspec, isawaitable, ismethod
from typing import TYPE_CHECKING, Any, Dict, List, Set, Union, cast

from starlette.routing import Router as StarletteRouter
from starlette.routing import WebSocketRoute
from starlette.types import Receive, Scope, Send

from starlite.exceptions import NotFoundException
from starlite.parsers import parse_path_params
from starlite.routes import ASGIRoute, HTTPRoute
from starlite.types import LifeCycleHandler

if TYPE_CHECKING:  # pragma: no cover
    from starlite.app import Starlite


class StarliteASGIRouter(StarletteRouter):
    """
    This class extends the Starlette Router class and *is* the ASGI app used in Starlite
    """

    def __init__(
        self,
        app: "Starlite",
        on_shutdown: List[LifeCycleHandler],
        on_startup: List[LifeCycleHandler],
    ):
        self.app = app
        super().__init__(on_startup=on_startup, on_shutdown=on_shutdown)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The main entry point to the Router class.
        """
        scope_type = scope["type"]
        path_params: List[str] = []
        path = cast(str, scope["path"]).strip()
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        if path in self.app.plain_routes:
            cur = self.app.route_map[path]
        else:
            cur = self.app.route_map
            components = ["/", *[component for component in path.split("/") if component]]
            for component in components:
                components_set = cast(Set[str], cur["_components"])
                if component in components_set:
                    cur = cast(Dict[str, Any], cur[component])
                elif "*" in components_set:
                    path_params.append(component)
                    cur = cast(Dict[str, Any], cur["*"])
                elif cur.get("static_path"):  # noqa: SIM106
                    scope_type = "asgi"
                    static_path = cast(str, cur["static_path"])
                    if static_path != "/":
                        scope["path"] = scope["path"].replace(static_path, "")
                else:  # noqa: SIM106
                    raise NotFoundException()
        try:
            handlers = cast(Dict[str, Any], cur["_handlers"])
            handler_types = cast(Set[str], cur["_handler_types"])
            route = cast(
                Union[WebSocketRoute, ASGIRoute, HTTPRoute],
                handlers[scope_type if scope_type in handler_types else "asgi"],
            )
            scope["path_params"] = parse_path_params(route.path_parameters, path_params) if route.path_parameters else {}  # type: ignore
        except KeyError as e:
            raise NotFoundException() from e
        else:
            await route.handle(scope=scope, receive=receive, send=send)

    async def call_lifecycle_handler(self, handler: LifeCycleHandler) -> None:
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
