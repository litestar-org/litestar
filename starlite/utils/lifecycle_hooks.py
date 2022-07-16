from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
    Union,
    overload,
)

from anyio.to_thread import run_sync
from typing_extensions import Literal

from .helpers import is_async_callable

if TYPE_CHECKING:
    from starlette.responses import Response as StarletteResponse

    from starlite.app import Starlite
    from starlite.connection import Request  # noqa: F401
    from starlite.controller import Controller
    from starlite.handlers import HTTPRouteHandler
    from starlite.router import Router
    from starlite.types import (
        AfterRequestHandler,
        AfterResponseHandler,
        BeforeRequestHandler,
    )

__all__ = ["AfterRequestHook", "AfterResponseHook", "BeforeRequestHook", "get_lifecycle_hook_from_layer"]

HandlerType = TypeVar("HandlerType", bound=Union["AfterRequestHandler", "AfterResponseHandler", "BeforeRequestHandler"])
ReceiveType = TypeVar("ReceiveType")
ReturnType = TypeVar("ReturnType")
ResponseType = TypeVar("ResponseType", bound="StarletteResponse")


class LifecycleHook(Generic[HandlerType, ReceiveType, ReturnType]):
    def __init__(self, fn: HandlerType) -> None:
        self.wrapped = [fn]  # wrap in list to prevent implicit binding
        self.fn_is_async = is_async_callable(fn)

    @property
    def hook(self) -> Callable[..., Any]:
        """The lifecycle hook"""
        return self.wrapped[0]

    async def __call__(self, arg: ReceiveType) -> ReturnType:
        if self.fn_is_async:
            return await self.hook(arg)  # type:ignore[no-any-return]
        return await run_sync(self.hook, arg)


AfterRequestHook = LifecycleHook["AfterRequestHandler", ResponseType, ResponseType]
AfterResponseHook = LifecycleHook["AfterResponseHandler", "Request", None]
BeforeRequestHook = LifecycleHook["BeforeRequestHandler", "Request", Any]

KeyType = Literal["after_request", "after_response", "before_request"]
LayerType = Union["Starlite", "Router", "Controller", "HTTPRouteHandler"]


@overload
def get_lifecycle_hook_from_layer(layer: LayerType, key: Literal["after_request"]) -> Optional[AfterRequestHook]:
    ...


@overload
def get_lifecycle_hook_from_layer(layer: LayerType, key: Literal["after_response"]) -> Optional[AfterResponseHook]:
    ...


@overload
def get_lifecycle_hook_from_layer(layer: LayerType, key: Literal["before_request"]) -> Optional[BeforeRequestHook]:
    ...


def get_lifecycle_hook_from_layer(layer: LayerType, key: KeyType) -> Optional[LifecycleHook]:
    """
    Get `LifecycleHook` instance from layer for attribute name `key`.

    Args:
        layer (Starlite | Router | Controller | HTTPRouteHandler): Hook retrieved from layer if it exists.
        key (Literal["after_request", "after_response", "before_request"]): Name of attribute on layer.

    Returns:
        LifecycleHook | None: The `LifecycleHook` instance if it exists, or `None`.
    """
    return getattr(layer, f"_{key}", getattr(layer, key))  # type:ignore[no-any-return]
