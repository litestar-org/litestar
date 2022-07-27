from inspect import getfullargspec, isawaitable, ismethod
from typing import TYPE_CHECKING, List

from starlette.routing import Router as StarletteRouter

from starlite.exceptions import NotFoundException

if TYPE_CHECKING:
    from starlette.types import Receive, Scope, Send

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

    async def __call__(self, scope: "Scope", receive: "Receive", send: "Send") -> None:
        """
        The main entry point to the Router class.
        """
        try:
            asgi_handler = self.app.route_map.resolve_asgi_app(scope)
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
