from inspect import getfullargspec, isawaitable
from typing import TYPE_CHECKING, Any, List

from starlette.routing import Router as StarletteRouter

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
        redirect_slashes: bool,
        on_shutdown: List[LifeCycleHandler],
        on_startup: List[LifeCycleHandler],
    ):
        self.app = app
        super().__init__(redirect_slashes=redirect_slashes, on_startup=on_startup, on_shutdown=on_shutdown)

    def __getattribute__(self, key: str) -> Any:
        """
        We override attribute access to return the app routes
        """
        if key == "routes":
            return self.app.routes
        return super().__getattribute__(key)

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
