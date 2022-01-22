from inspect import getfullargspec, isawaitable
from typing import TYPE_CHECKING, Any, List, cast, Set, Dict, Union

from starlette.routing import Router as StarletteRouter, WebSocketRoute
from starlette.types import Scope, Receive, Send

from starlite.exceptions import NotFoundException
from starlite.types import LifeCycleHandler
from starlite.routing import HTTPRoute

if TYPE_CHECKING:  # pragma: no cover
    from starlite.app import Starlite


class StarliteASGIRouter(StarletteRouter):
    """
    This class extends the Starlette Router class and *is* the ASGI app used in Starlite
    """

    def __init__(
        self,
        app: "Starlite",
        redirect_slashes: bool,
        on_shutdown: List[LifeCycleHandler],
        on_startup: List[LifeCycleHandler],
    ):
        self.app = app
        super().__init__(redirect_slashes=redirect_slashes, on_startup=on_startup, on_shutdown=on_shutdown)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        The main entry point to the Router class.
        """

        scope_type = scope["type"]

        if scope_type == "lifespan":
            await self.lifespan(scope, receive, send)
            return
        path_params: List[str] = []
        path = cast(str, scope["path"]).strip()
        if path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        components = path.split("/") if path != "/" else ["_root"]
        cur = self.app.route_map
        for component in components:
            components_set = cast(Set[str], cur["_components"])
            if component in components_set:
                cur = cast(Dict[str, Any], cur[component])
            elif "*" in components_set:
                path_params.append(component)
                cur = cast(Dict[str, Any], cur["*"])
            else:
                raise NotFoundException()
        handlers = cast(Dict[str, Any], cur["_handlers"])
        try:
            route = cast(Union[WebSocketRoute, HTTPRoute], handlers[scope_type])
            scope["path_params"] = route.parse_path_params(path_params)
            await route.handle(scope=scope, receive=receive, send=send)
        except KeyError:
            raise NotFoundException()

    async def call_lifecycle_handler(self, handler: LifeCycleHandler) -> None:
        """
        Determines whether the lifecycle handler expects an argument, and if so passed the app.state to it.
        If the handler is an async function, it awaits the return.
        """
        arg_spec = getfullargspec(handler)
        if arg_spec.args:
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
