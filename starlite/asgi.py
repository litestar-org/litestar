from inspect import getfullargspec, isawaitable, ismethod
from typing import TYPE_CHECKING, Any, Dict, List, Set, Tuple, cast

from starlette.routing import Router as StarletteRouter
from starlette.types import ASGIApp, Receive, Scope, Send

from starlite.enums import ScopeType
from starlite.exceptions import MethodNotAllowedException, NotFoundException
from starlite.parsers import parse_path_params

if TYPE_CHECKING:  # pragma: no cover
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

    def parse_scope_to_route(self, scope: Scope) -> Tuple[Dict[str, ASGIApp], bool]:
        """
        Given a scope object, retrieve the _asgi_handlers and _is_asgi values from correct trie node.
        
        Raises NotFoundException if no correlating node is found for the scope's path
        """
        return self.app.route_map.parse_scope_to_route(scope, parse_path_params)

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
