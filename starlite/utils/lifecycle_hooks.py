from functools import partial
from typing import (
    TYPE_CHECKING,
    Any,
    Awaitable,
    Callable,
    Dict,
    Generic,
    Optional,
    Tuple,
    TypeVar,
    Union,
)

from anyio.to_thread import run_sync
from typing_extensions import Literal  # noqa: TC002

from .helpers import is_async_callable

if TYPE_CHECKING:

    from starlite.handlers.base import BaseRouteHandler

_ReturnValue = TypeVar("_ReturnValue")


class LifecycleHook(Generic[_ReturnValue]):
    def __init__(
        self,
        route_handler: "BaseRouteHandler",
        method_key: Union[Literal["before_request"], Literal["after_request"], Literal["after_response"]],
    ) -> None:
        self.hook: Optional[Tuple[Callable[..., Awaitable[_ReturnValue]]]] = None
        for layer in route_handler.ownership_layers:
            layer_hook = getattr(layer, method_key, None)
            if layer_hook:
                # wrap in list to prevent implicit binding
                if is_async_callable(layer_hook):
                    self.hook = (layer_hook,)
                else:
                    self.hook = (partial(run_sync, layer_hook),)  # type: ignore[assignment]

    async def __call__(self, *args: Any, **kwargs: Dict[str, Any]) -> Optional[_ReturnValue]:
        if self.hook:
            return await self.hook[0](*args, **kwargs)
        return None
