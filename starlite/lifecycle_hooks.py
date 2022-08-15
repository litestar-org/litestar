from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Generic,
    Optional,
    Type,
    TypeVar,
    Union,
)

from anyio.to_thread import run_sync
from typing_extensions import Literal

from starlite.utils import is_async_callable

if TYPE_CHECKING:
    from starlette.responses import Response as StarletteResponse

    from starlite.handlers.http import HTTPRouteHandler
    from starlite.response import Response

H = TypeVar("H", bound="LifecycleHook")
R = TypeVar("R")


class LifecycleHook(Generic[R]):
    """Abstracts handler resolution and provides eager discrimination of sync
    vs.

    async handlers.
    """

    def __init__(self, handler: Union[Callable[..., R], Callable[..., Awaitable[R]]]) -> None:
        self.handler: Callable[..., Awaitable[R]]
        if is_async_callable(handler):
            self.handler = handler  # type:ignore[assignment]
        else:
            self.handler = partial(run_sync, handler)  # type:ignore[assignment]

    async def __call__(self, *args: Any) -> R:
        return await self.handler(*args)

    @classmethod
    def resolve_for_handler(
        cls: Type[H],
        route_handler: "HTTPRouteHandler",
        attribute_key: Literal["after_request", "after_response", "before_request"],
    ) -> Optional[H]:
        """Resolves `attribute_key` for `route_handler`.

        If a hook is registered, returns an instance of `LifecycleHook`, otherwise returns `None`.

        Args:
            route_handler (HTTPRouteHandler): the handler to have the hook resolved.
            attribute_key (Literal["after_request", "after_response", "before_request"]): attribute of hook on layer.

        Returns:
            HTTPRouteHandler | None
        """
        handler = None
        for layer in route_handler.ownership_layers:
            layer_handler = getattr(layer, attribute_key, None)
            if layer_handler:
                handler = layer_handler

        if handler is None:
            return None
        return cls(handler=handler)


ResponseType = Union["Response", "StarletteResponse"]
AfterRequestHook = LifecycleHook[ResponseType]
AfterResponseHook = LifecycleHook[None]
BeforeRequestHook = LifecycleHook[Optional[ResponseType]]
