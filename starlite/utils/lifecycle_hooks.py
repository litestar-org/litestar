from functools import partial
from typing import Any, Callable

from anyio.to_thread import run_sync

from .helpers import is_async_callable


class LifecycleHook:
    def __init__(self, handler: Callable[..., Any]) -> None:
        if is_async_callable(handler):
            self.wrapped = [handler]  # wrap in list to prevent implicit binding
        else:
            self.wrapped = [partial(run_sync, handler)]

    async def __call__(self, *args: Any) -> Any:
        return await self.wrapped[0](*args)
